"""Worker do `edin imagem` e do `edin profundidade`: roda no venv SEPARADO (~/.local/share/edin/imagem/venv, com
PyTorch CUDA + diffusers + transformers), chamado pelo edin por subprocesso com `python -I`. Não importa nada do
pacote edin (no modo -I a pasta do script não entra no sys.path): é autocontido.

    python -I imagem_worker.py baixar  <modelos_imagem.json> <pasta_modelos>
    python -I imagem_worker.py gerar   <job.json>      (SDXL + LoRA Lightning de 4 passos)
    python -I imagem_worker.py profundidade <job.json> (Depth Anything V2 Small)
    python -I imagem_worker.py info

Progresso e resultados saem no stdout como linhas JSON ({"evento": ...}); o resto (avisos das bibliotecas) vai
para o stderr.

Memória (RTX 4050 de 6 GB): o SDXL fp16 tem 6,9 GB de pesos, não cabe inteiro. Em vez do offload automático
(que leva a UNet de 5 GB para a GPU e de volta a cada imagem), o lote anda em estágios: (1) os dois text encoders
na GPU codificam todos os prompts; (2) só a UNet (com o LoRA fundido) na GPU gera todos os latentes; (3) só o VAE
em fp32 decodifica, com tiling se faltar memória. Cada estágio carrega um modelo por vez.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


def emit(**kw):
    print(json.dumps(kw, ensure_ascii=False), flush=True)


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------------------------------- baixar
def baixar(manifesto: str, destino: str):
    from huggingface_hub import hf_hub_download

    cfg = json.loads(Path(manifesto).read_text())
    base = Path(destino)
    for nome, m in cfg["modelos"].items():
        pasta = base / m["pasta"]
        for arq, tam in m["arquivos"].items():
            alvo = pasta / arq
            if alvo.exists() and alvo.stat().st_size == tam:
                continue
            log(f"[edin imagem] baixando {m['repo']}/{arq} ({tam / 1e6:.0f} MB)")
            hf_hub_download(m["repo"], arq, revision=m["revisao"], local_dir=str(pasta))
            real = alvo.stat().st_size
            if real != tam:
                raise SystemExit(f"tamanho errado em {alvo}: {real} (esperado {tam})")
        total = sum(m["arquivos"].values())
        emit(evento="modelo", nome=nome, repo=m["repo"], pasta=str(pasta), mb=round(total / 1e6))
    emit(evento="fim")


# ---------------------------------------------------------------------------------------------------- gerar
def _vram():
    import torch

    return round(torch.cuda.max_memory_reserved() / 2**20)


def gerar(job_path: str):
    import torch
    from diffusers import EulerDiscreteScheduler, StableDiffusionXLPipeline

    job = json.loads(Path(job_path).read_text())
    itens = job["itens"]
    sdxl, lora = job["sdxl"], job.get("lora")
    cuda = torch.device("cuda")
    if not torch.cuda.is_available():
        raise SystemExit("PyTorch sem CUDA: o edin imagem precisa de GPU NVIDIA (ver docs/IMAGEM.md)")

    class Pipe(StableDiffusionXLPipeline):
        # os módulos ficam em dispositivos diferentes por estágio; a execução é sempre na GPU
        @property
        def _execution_device(self):
            return cuda

    t0 = time.time()
    pipe = Pipe.from_pretrained(sdxl, torch_dtype=torch.float16, variant="fp16", use_safetensors=True,
                                local_files_only=True, add_watermarker=False)
    pipe.set_progress_bar_config(disable=True)
    t_carga = time.time() - t0
    torch.cuda.reset_peak_memory_stats()

    # ---- 1) prompts (os dois CLIP na GPU, ~1,6 GB)
    t1 = time.time()
    pipe.text_encoder.to(cuda)
    pipe.text_encoder_2.to(cuda)
    emb = []
    with torch.inference_mode():
        for it in itens:
            cfg = float(it.get("cfg", 0))
            ntok = len(pipe.tokenizer(it["prompt"]).input_ids)
            pe, ne, pp, npp = pipe.encode_prompt(it["prompt"], device=cuda, num_images_per_prompt=1,
                                                 do_classifier_free_guidance=cfg > 1,
                                                 negative_prompt=it.get("negativo") or None)
            mv = lambda x: None if x is None else x.to("cpu")
            emb.append((mv(pe), mv(ne), mv(pp), mv(npp), ntok))
    pipe.text_encoder.to("cpu")
    pipe.text_encoder_2.to("cpu")
    torch.cuda.empty_cache()
    t_texto = time.time() - t1
    vram_texto = _vram()

    # ---- 2) UNet (5,1 GB) com o LoRA Lightning fundido, na GPU sozinha
    t2 = time.time()
    if lora:
        # funde o LoRA na UNet (fp16, na CPU: não precisa de VRAM extra) e descarta os pesos dele
        pipe.load_lora_weights(str(Path(lora).parent), weight_name=Path(lora).name)
        pipe.fuse_lora()
        pipe.unload_lora_weights()
        pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")
    modo = job.get("memoria", "auto")
    if modo == "camadas":
        pipe.unet.enable_group_offload(onload_device=cuda, offload_type="leaf_level", use_stream=True)
    else:
        pipe.unet.to(cuda)
    t_unet = time.time() - t2
    torch.cuda.reset_peak_memory_stats()
    latentes = []

    def denoise(it, emb_i):
        pe, ne, pp, npp, _ = emb_i
        cfg = float(it.get("cfg", 0))
        g = torch.Generator("cpu").manual_seed(int(it["seed"]))
        kw = dict(prompt_embeds=pe.to(cuda), pooled_prompt_embeds=pp.to(cuda))
        if cfg > 1:
            kw.update(negative_prompt_embeds=ne.to(cuda), negative_pooled_prompt_embeds=npp.to(cuda))
        return pipe(width=int(it["w"]), height=int(it["h"]), num_inference_steps=int(it["passos"]),
                    guidance_scale=cfg if cfg > 1 else 0.0, generator=g, output_type="latent", **kw).images

    with torch.inference_mode():
        for i, it in enumerate(itens):
            ts = time.time()
            try:
                lat = denoise(it, emb[i])
            except torch.cuda.OutOfMemoryError:
                if modo == "camadas":
                    raise
                # não coube a UNet inteira (5,1 GB) + ativações: offload por camadas com stream (mesma imagem)
                log("[edin imagem] VRAM insuficiente para a UNet inteira; usando offload por camadas")
                pipe.unet.to("cpu")
                torch.cuda.empty_cache()
                pipe.unet.enable_group_offload(onload_device=cuda, offload_type="leaf_level", use_stream=True)
                modo = "camadas"
                ts = time.time()
                lat = denoise(it, emb[i])
            torch.cuda.synchronize()
            latentes.append(lat.to("cpu"))
            emit(evento="latente", i=i, segundos=round(time.time() - ts, 2), tokens=emb[i][4], memoria=modo)
    vram_unet = _vram()
    if modo != "camadas":
        pipe.unet.to("cpu")
    pipe.unet = None
    torch.cuda.empty_cache()

    # ---- 3) VAE em fp32 (o VAE do SDXL estoura em fp16: force_upcast)
    t3 = time.time()
    vae = pipe.vae.to(cuda, dtype=torch.float32)
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    tiling = False
    with torch.inference_mode():
        for i, it in enumerate(itens):
            ts = time.time()
            lat = latentes[i].to(cuda, torch.float32) / vae.config.scaling_factor
            try:
                img = vae.decode(lat).sample
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                vae.enable_tiling()
                tiling = True
                img = vae.decode(lat).sample
            pil = pipe.image_processor.postprocess(img, output_type="pil")[0]
            Path(it["saida"]).parent.mkdir(parents=True, exist_ok=True)
            pil.save(it["saida"])
            emit(evento="imagem", i=i, saida=it["saida"], segundos=round(time.time() - ts, 2))
    vram_vae = _vram()
    emit(evento="fim", carga_s=round(t_carga, 1), texto_s=round(t_texto, 1), unet_carga_s=round(t_unet, 1),
         vae_s=round(time.time() - t3, 1), vram_mb={"texto": vram_texto, "unet": vram_unet, "vae": vram_vae},
         vae_tiling=tiling, memoria=modo, gpu=torch.cuda.get_device_name(0), torch=torch.__version__)


# ---------------------------------------------------------------------------------------------------- profundidade
def profundidade(job_path: str):
    import numpy as np
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation

    job = json.loads(Path(job_path).read_text())
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    t0 = time.time()
    proc = AutoImageProcessor.from_pretrained(job["modelo"], local_files_only=True)
    model = AutoModelForDepthEstimation.from_pretrained(job["modelo"], local_files_only=True).to(dev).eval()
    emit(evento="carga", segundos=round(time.time() - t0, 2), dispositivo=str(dev))
    for it in job["itens"]:
        ts = time.time()
        im = Image.open(it["entrada"]).convert("RGB")
        lado = int(it.get("lado", 770))
        # lado menor = `lado` (múltiplo de 14), proporção mantida: bordas mais finas que os 518 padrão
        w, h = im.size
        if w <= h:
            nw, nh = lado, round(h * lado / w / 14) * 14
        else:
            nh, nw = lado, round(w * lado / h / 14) * 14
        inp = proc(images=im, return_tensors="pt", size={"height": nh, "width": nw}, keep_aspect_ratio=False,
                   do_resize=True)
        with torch.inference_mode():
            pred = model(pixel_values=inp["pixel_values"].to(dev)).predicted_depth
            pred = torch.nn.functional.interpolate(pred[:, None], size=(h, w), mode="bicubic", align_corners=False)
        d = pred[0, 0].float().cpu().numpy().astype("float32")
        np.save(it["saida"], d)
        emit(evento="profundidade", entrada=it["entrada"], saida=it["saida"], segundos=round(time.time() - ts, 2),
             entrada_rede=[nw, nh])
    emit(evento="fim", vram_mb=round(torch.cuda.max_memory_reserved() / 2**20) if dev.type == "cuda" else 0)


def info():
    import torch

    r = {"torch": torch.__version__, "cuda": torch.version.cuda, "gpu": torch.cuda.is_available()}
    if r["gpu"]:
        p = torch.cuda.get_device_properties(0)
        r.update(nome=p.name, vram_mb=round(p.total_memory / 2**20))
    for mod in ("diffusers", "transformers", "accelerate", "peft", "safetensors"):
        try:
            r[mod] = __import__(mod).__version__
        except Exception as e:  # noqa: BLE001
            r[mod] = f"FALTA ({e.__class__.__name__})"
    emit(evento="info", **r)


if __name__ == "__main__":
    os.environ.setdefault("HF_HUB_OFFLINE", "0" if sys.argv[1:2] == ["baixar"] else "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "info"
    if cmd == "baixar":
        baixar(sys.argv[2], sys.argv[3])
    elif cmd == "gerar":
        gerar(sys.argv[2])
    elif cmd == "profundidade":
        profundidade(sys.argv[2])
    else:
        info()
