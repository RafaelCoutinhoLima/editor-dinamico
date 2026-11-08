"""Renderização do plano: corta, reenquadra, dá zoom, aplica b-roll, legenda, SFX, música e normaliza o áudio."""
from __future__ import annotations

import shutil
from pathlib import Path

from .captions import build_ass
from .plan import load_plan, remap_words, seg_out_dur, seg_src
import numpy as np

from .reframe import (CAM_FPS, activity_pan, activity_window, camera_path, crop_box, face_track, face_window, focus_for,
                      piecewise_expr, reframe_cfg, simplify_keys)
from .scenes import shots
from .sfx import VOLUME as SFX_VOLUME
from .sfx import sfx_file, sync_start
from .utils import FONTS_DIR, ffmpeg_filter_path, is_image, load_json, probe, run, workdir_for

FORMATS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}


def _even(x: float) -> int:
    return int(round(x / 2) * 2)


def out_size(plan: dict, main: dict, draft: bool):
    fmt = plan.get("format", "9:16")
    if fmt in FORMATS:
        w, h = FORMATS[fmt]
    else:  # original
        s = min(1.0, 1920 / max(main["w"], main["h"]))
        w, h = _even(main["w"] * s), _even(main["h"] * s)
    if draft:
        w, h = _even(w / 2), _even(h / 2)
    return w, h


def _atempo(speed: float) -> str:
    parts, s = [], speed
    while s > 2.0:
        parts.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        parts.append("atempo=0.5")
        s /= 0.5
    parts.append(f"atempo={s:.4f}")
    return ",".join(parts)


class Renderer:
    def __init__(self, plan: dict, output: str, draft: bool = False, verbose: bool = False):
        self.plan, self.output, self.draft, self.verbose = plan, output, draft, verbose
        self.wd = workdir_for(output)
        self.cache = self.wd / "cache"
        self.cache.mkdir(exist_ok=True)
        self._probe, self._tracks = {}, {}
        self._pad = None
        self._pan = None
        self._hide = None
        self._dim = 0.22
        self.camera_log = []  # trajetórias da câmera virtual (para medir tremor e conferir)
        main = self.info(plan["source"])
        self.W, self.H = out_size(plan, main, draft)
        self.fps = float(plan.get("fps", 30))
        self.crf = 28 if draft else 18
        self.preset = "ultrafast" if draft else "veryfast"

    def info(self, src):
        if src not in self._probe:
            self._probe[src] = probe(src)
        return self._probe[src]

    def track(self, src):
        if src not in self._tracks:
            print(f"[edin] Detectando rosto em {Path(src).name}...")
            self._tracks[src] = face_track(src, self.cache)
        return self._tracks[src]

    # ------------------------------------------------------------ vídeo de um segmento
    def _blur_fill(self, zoom: float = 1.0, drift: float = 1.0, d_out: float = 1.0, pad_color: str | None = None) -> str:
        """Fonte inteira no centro + cópia desfocada preenchendo as laterais (não corta cabeça nem testa).
        drift > 1 aproxima o quadro todo devagar ao longo do segmento (zoom_to / zoom)."""
        W, H = self.W, self.H
        fw, fh = _even(W * zoom), _even(H * zoom)
        if pad_color:  # fundo de cor sólida no lugar do desfoque
            chain = (f"scale={fw}:{fh}:force_original_aspect_ratio=decrease:flags=lanczos,"
                     f"pad=w='max(iw,{W})':h='max(ih,{H})':x=(ow-iw)/2:y=(oh-ih)/2:color={pad_color},"
                     f"crop={W}:{H}")
        else:
            chain = (f"split=2[bf_bg][bf_fg];[bf_bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                     f"boxblur=40:3,eq=brightness={-self._dim:.3f}:saturation=1.15[bf_b];[bf_fg]scale={fw}:{fh}"
                     f":force_original_aspect_ratio=decrease:flags=lanczos[bf_f];[bf_b][bf_f]overlay=(W-w)/2:(H-h)/2")
        if abs(drift - 1.0) > 1e-3:
            n = max(1, int(round(d_out * self.fps)) - 1)
            up = 1.0 if self.draft else 1.5
            a, b = (1.0, drift) if drift > 1 else (1 / drift, 1.0)
            chain += (f",scale={_even(W * up)}:{_even(H * up)}:flags=bicubic,zoompan=z='{a:.4f}+({b - a:.4f})*on/{n}'"
                      f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={self.fps}")
        return chain + f",fps={self.fps},setsar=1,format=yuv420p"

    def _extend_fill(self, src_ar: float, zoom: float, drift: float, d_out: float) -> str:
        """Quadro inteiro no centro e as bordas da própria cena esticadas até o topo/base/laterais e suavizadas.
        Emenda sem faixa em fundos lisos ou com degradê (cenas de texto, logos, motion)."""
        W, H = self.W, self.H
        bw, bh = W * zoom, H * zoom
        fw, fh = (bw, bw / src_ar) if src_ar > bw / bh else (bh * src_ar, bh)
        fw, fh = _even(fw), _even(fh)
        # fundo: o quarto de cima e o de baixo da própria cena, espelhados, esticados até as bordas e desfocados.
        # Sem vstack/fillborders nem ampliar tiras finas: no ffmpeg 8 isso corrompia memória e deixava a base preta.
        top = max(0, (H - fh) // 2)
        bot = max(0, H - fh - top)
        cw = max(fw, W)
        q = max(8, _even(fh / 40))  # tira fina da borda (2,5%): só fundo; faixas maiores pegavam botão/ícone e viravam mancha
        chain = f"scale={fw}:{fh}:flags=lanczos,split=4[ex_a][ex_t][ex_c][ex_b];"
        chain += f"[ex_c]pad={cw}:{fh + top + bot}:{(cw - fw) // 2}:{top}[ex_cv];"
        cur = "[ex_cv]"
        if top:
            chain += f"[ex_t]crop={fw}:{q}:0:0,vflip,scale={fw}:{top}[ex_tt];{cur}[ex_tt]overlay={(cw - fw) // 2}:0[ex_c1];"
            cur = "[ex_c1]"
        else:
            chain += "[ex_t]nullsink;"
        if bot:
            chain += (f"[ex_b]crop={fw}:{q}:0:{fh - q},vflip,scale={fw}:{bot}[ex_bb];"
                      f"{cur}[ex_bb]overlay={(cw - fw) // 2}:{top + fh}[ex_c2];")
            cur = "[ex_c2]"
        else:
            chain += "[ex_b]nullsink;"
        if cw > fw:  # laterais (fonte mais estreita que a saída): espelha o quarto da esquerda e da direita
            side = (cw - fw) // 2
            qw = max(8, _even(fw / 40))
            chain += (f"{cur}split=3[ex_m][ex_l][ex_r];[ex_l]crop={qw}:ih:{side}:0,hflip,scale={side}:ih[ex_ll];"
                      f"[ex_r]crop={qw}:ih:{side + fw - qw}:0,hflip,scale={cw - fw - side}:ih[ex_rr];"
                      f"[ex_m][ex_ll]overlay=0:0[ex_m1];[ex_m1][ex_rr]overlay={side + fw}:0[ex_c3];")
            cur = "[ex_c3]"
        chain += (f"{cur}crop={W}:{H},boxblur=30:2[ex_bg];"
                  f"[ex_a]crop='min(iw,{W})':'min(ih,{H})'[ex_fg];[ex_bg][ex_fg]overlay=(W-w)/2:(H-h)/2")
        if abs(drift - 1.0) > 1e-3:
            n = max(1, int(round(d_out * self.fps)) - 1)
            up = 1.0 if self.draft else 1.5
            chain += (f",scale={_even(W * up)}:{_even(H * up)}:flags=bicubic,zoompan=z='1+({drift - 1:.4f})*on/{n}'"
                      f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={self.fps}")
        return chain + f",fps={self.fps},setsar=1,format=yuv420p"

    # ------------------------------------------------------------ câmera virtual e pan, por plano
    def _shots(self, src: str, t0: float, t1: float) -> list:
        """Planos do trecho [t0, t1] da fonte (cortes do PySceneDetect). A câmera recomeça em cada um."""
        if is_image(src):
            return [(t0, t1)]
        try:
            return shots(src, t0, t1)
        except Exception as e:  # sem PySceneDetect ou vídeo ilegível: trecho inteiro como um plano só
            print(f"\n[edin] Aviso: detecção de cenas falhou ({e}); câmera sem divisão por plano.")
            return [(t0, t1)]

    def _shot_targets(self, src: str, a: float, b: float, focus: str, view: tuple, cfg: dict):
        """Alvo da câmera num plano: (amostras, tem_rosto, parado_rápido).
        `parado_rápido` = (fx, fy) quando o rastreio de 2 fps já mostra que o rosto quase não sai do lugar
        (mesmo resultado do enquadramento parado de antes, sem custo extra)."""
        dzx, dzy = cfg["deadzone"] * view[0], cfg["deadzone"] * view[1]
        if cfg["mode"] != "track":
            g = [f for f in self.track(src) if a <= f["t"] <= b]
            if len(g) >= 2 and max(f["x"] for f in g) - min(f["x"] for f in g) <= 2 * dzx \
                    and max(f["y"] for f in g) - min(f["y"] for f in g) <= 2 * dzy:
                return None, True, focus_for(self.track(src), a, b)[0]
        faces = face_window(src, a, b, self.cache)
        if len(faces) >= 0.25 * (b - a) * CAM_FPS:
            return faces, True, None
        # rosto em menos de 25% das amostras (de perfil, no escuro, longe): não é confiável para guiar a câmera
        # (detecções falsas viram a semente). Segue o que se mexe de verdade, com compensação do movimento da câmera.
        act = activity_window(src, a, b, self.cache)
        motion = [s for s in act if s["kind"] == "motion"]
        if len(motion) >= 0.3 * max(1, len(act)):
            return motion, False, None
        if focus == "face" or not act:
            return None, True, focus_for(self.track(src), a, b)[0]
        return act, False, None  # "auto" sem rosto e sem movimento: saliência

    def _camera(self, src: str, t0: float, t1: float, focus: str, zmin: float, speed: float, cfg: dict):
        """Expressões (x, y) do recorte com a câmera virtual, ou None quando o resultado é um enquadramento parado
        num plano só (aí vale o crop fixo de sempre, idêntico ao de antes)."""
        info = self.info(src)
        sw, sh = info["w"], info["h"]
        _, _, cw, ch = crop_box(sw, sh, self.W, self.H, zmin, 0.5, 0.5, False)
        view = (cw / sw, ch / sh)
        pieces = self._shots(src, t0, t1)
        keys_x, keys_y, moving = [], [], False
        for k, (a, b) in enumerate(pieces):
            samples, has_face, still = self._shot_targets(src, a, b, focus, view, cfg)
            if still is None:
                sx, px = camera_path(samples, a, b, view[0], cfg, "x")
                sy, py = camera_path(samples, a, b, view[1], cfg, "y")
                if sx and sy:
                    still = (0.5 if px is None else px, 0.5 if py is None else py)
            ta, tb = (a - t0) / speed, (b - t0) / speed
            if still is not None:
                fx, fy = still
                cx, cy, *_ = crop_box(sw, sh, self.W, self.H, zmin, fx, fy, has_face)
                xs, ys, ts = [cx, cx], [cy, cy], [ta, tb]
                mode = "parado"
            else:
                moving = True
                grid = px[0] if not sx else py[0]
                gx = np.full(len(grid), px) if sx else px[1]
                gy = np.full(len(grid), py) if sy else py[1]
                boxes = [crop_box(sw, sh, self.W, self.H, zmin, float(x), float(y), has_face) for x, y in zip(gx, gy)]
                ts = [(t - t0) / speed for t in grid]
                xs, ys = [bx[0] for bx in boxes], [bx[1] for bx in boxes]
                mode = "segue"
            if self.verbose:
                print(f"\n[edin] câmera plano {k + 1}/{len(pieces)} [{a:.2f}-{b:.2f}] "
                      f"{'rosto' if has_face else 'atividade'} {mode}")
            if k:  # corte: a câmera salta junto com a imagem (nunca desliza de um plano para o outro)
                ta_cut = ta - 0.01
                keys_x += [(ta_cut, keys_x[-1][1]), (ta_cut + 0.005, xs[0])]
                keys_y += [(ta_cut, keys_y[-1][1]), (ta_cut + 0.005, ys[0])]
            keys_x += simplify_keys(ts, xs)
            keys_y += simplify_keys(ts, ys)
        if len(pieces) == 1 and not moving:
            return None
        self.camera_log.append({"src": src, "t0": t0, "t1": t1, "x": keys_x})
        return piecewise_expr(keys_x), piecewise_expr(keys_y)

    def _pan_expr(self, src: str, t0: float, t1: float, zmin: float, fy: float, has_face: bool, d_out: float,
                  speed: float) -> str:
        """x(t) do `pan`. Num plano só: easing de pan[0] a pan[1] no segmento inteiro (como sempre foi).
        Com corte no meio: recomeça em cada plano. `"auto"` mede cada plano; manual faz o movimento no plano mais
        longo e fica parado nos outros (antes: pan[0]; depois: pan[1])."""
        info = self.info(src)
        _, _, cw, _ = crop_box(info["w"], info["h"], self.W, self.H, zmin, 0.5, fy, has_face)
        view = cw / info["w"]
        pieces = self._shots(src, t0, t1)
        if len(pieces) == 1:
            pans = [self._pan]
            if self._pan == "auto":  # câmera segue a atividade da tela (cursor, digitação, elementos entrando)
                pans = [activity_pan(src, t0, t1, view, self.cache)]
                print(f"\r[edin] pan automático {pans[0][0]:.2f} -> {pans[0][1]:.2f}", end="")
        elif self._pan == "auto":
            pans = [activity_pan(src, a, b, view, self.cache) for a, b in pieces]
            print(f"\r[edin] pan automático por plano: {' | '.join(f'{p[0]:.2f}->{p[1]:.2f}' for p in pans)}", end="")
        else:
            big = max(range(len(pieces)), key=lambda i: pieces[i][1] - pieces[i][0])
            x0, x1 = self._pan
            pans = [[x0, x0] if i < big else [x0, x1] if i == big else [x1, x1] for i in range(len(pieces))]

        def px(x):
            return crop_box(info["w"], info["h"], self.W, self.H, zmin, float(x), fy, has_face)[0]

        if len(pieces) == 1:
            x0, x1 = px(pans[0][0]), px(pans[0][1])
            return f"{x0}+({x1 - x0})*(0.5-0.5*cos(PI*min(t/{d_out:.3f},1)))"
        expr = None
        for (a, b), p in reversed(list(zip(pieces, pans))):
            x0, x1 = px(p[0]), px(p[1])
            ta, da = (a - t0) / speed, (b - a) / speed
            e = f"{x0}+({x1 - x0})*(0.5-0.5*cos(PI*min(max(t-{ta:.3f},0)/{da:.3f},1)))"
            expr = e if expr is None else f"if(lt(t,{(b - t0) / speed - 0.01:.3f}),{e},{expr})"
        return expr

    def _vchain(self, src: str, t0: float, t1: float, zoom: float, zoom_to: float, focus, d_out: float,
                fit: str | None = None, speed: float = 1.0, reframe=None) -> str:
        info = self.info(src)
        # "blur": mostra o quadro inteiro com fundo desfocado. Automático quando a fonte é vertical e a saída
        # horizontal (o crop cortaria a testa e o queixo).
        src_ar, out_ar = info["w"] / info["h"], self.W / self.H
        if fit == "extend":
            z = max(1.0, zoom)
            return self._extend_fill(src_ar, z, max(1.0, zoom_to) / z, d_out)
        if fit in ("blur", "pad") or (fit is None and src_ar < out_ar * 0.75):
            z = max(1.0, zoom)
            color = None
            if fit == "pad":
                color = "0x" + str(self._pad or self.plan.get("pad_color", "#000000")).lstrip("#")
            return self._blur_fill(z, max(1.0, zoom_to) / z, d_out, color)
        if focus == "center" or focus is None:
            (fx, fy), has_face = (0.5, 0.5), False
        elif isinstance(focus, (list, tuple)):
            (fx, fy), has_face = (float(focus[0]), float(focus[1])), True
        else:
            (fx, fy), has_face = focus_for(self.track(src), t0, t1)
        zoom, zoom_to = max(1.0, zoom), max(1.0, zoom_to)  # zoom < 1 cortaria fora do quadro
        zmin = min(zoom, zoom_to)
        cx, cy, cw, ch = crop_box(info["w"], info["h"], self.W, self.H, zmin, fx, fy, has_face)
        chain = [f"crop={cw}:{ch}:{cx}:{cy}"]
        if focus in ("face", "auto") and not self._pan and not is_image(src):
            cam = self._camera(src, t0, t1, focus, zmin, speed, reframe_cfg(reframe))
            if cam:  # câmera virtual: x(t)/y(t) por expressão; exact=1 anda de 1 em 1 px (sem degrau de 2 px)
                chain = [f"crop={cw}:{ch}:'{cam[0]}':'{cam[1]}':exact=1"]
        if self._pan:  # câmera lateral: o recorte anda de pan[0] até pan[1] (x normalizado) com easing suave
            chain = [f"crop={cw}:{ch}:'{self._pan_expr(src, t0, t1, zmin, fy, has_face, d_out, speed)}':{cy}"]
        if self._hide:  # esconde regiões da fonte (legenda/rótulo gravado) com uma cópia desfocada e escurecida
            pre = []
            for k, (x0, y0, x1, y1) in enumerate(self._hide):
                rx, ry = _even(x0 * info["w"]), _even(y0 * info["h"])
                rw, rh = _even((x1 - x0) * info["w"]), _even((y1 - y0) * info["h"])
                # borda suave: a cópia desfocada some aos poucos nos 20% finais da região (sem linha dura)
                pre.append(f"split[hd{k}a][hd{k}b];[hd{k}b]crop={rw}:{rh}:{rx}:{ry},boxblur=24:3,"
                           f"eq=brightness=-0.25,format=yuva420p,geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)'"
                           f":a='255*min(1,(H-Y)/(H*0.2))'[hd{k}c];[hd{k}a][hd{k}c]overlay={rx}:{ry}:format=auto")
            pre[-1] += ",format=yuv420p"
            chain = pre + chain
        if abs(zoom_to - zoom) > 1e-3:
            a, b = zoom / zmin, zoom_to / zmin
            n = max(1, int(round(d_out * self.fps)) - 1)
            up = 1.5 if not self.draft else 1.0
            chain += [f"scale={_even(self.W * up)}:{_even(self.H * up)}:flags=bicubic",
                      f"zoompan=z='{a:.4f}+({b - a:.4f})*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                      f":d=1:s={self.W}x{self.H}:fps={self.fps}"]
        else:
            chain.append(f"scale={self.W}:{self.H}:flags=lanczos")
        chain += [f"fps={self.fps}", "setsar=1", "format=yuv420p"]
        return ",".join(chain)

    def render_segment(self, i: int, seg: dict) -> Path:
        # .mov com áudio PCM: o concat junta amostra por amostra. Com AAC em .mp4 cada segmento trazia áudio
        # mais longo que o vídeo (quadros de 1024 amostras + priming), o concat empilhava timestamps para trás
        # e o mux final abria saltos de segundos no áudio (fala comida e boca fora de sincronia).
        out = self.wd / f"seg_{i:04d}.mov"
        self._pad = seg.get("pad_color")  # cor de fundo do fit "pad" só deste segmento
        self._pan = seg.get("pan")  # [x_inicio, x_fim] normalizados: câmera lateral dentro do segmento
        self._dim = float(seg.get("blur_dim", 0.22))  # quanto escurecer o fundo do fit "blur" (0 = nada)
        self._hide = seg.get("hide")  # [[x0, y0, x1, y1], ...] normalizados na fonte: regiões a esconder
        src = seg_src(self.plan, seg)
        speed = float(seg.get("speed", 1.0) or 1.0)
        d_src = seg["end"] - seg["start"]
        # duração quantizada em quadros: áudio e vídeo do segmento com exatamente o mesmo tamanho
        d_out = max(1, round(d_src / speed * self.fps)) / self.fps
        zoom = float(seg.get("zoom", 1.0))
        zoom_to = float(seg.get("zoom_to", zoom))
        cmd = ["ffmpeg", "-y", "-v", "error"]
        broll = seg.get("broll")
        if broll:
            bsrc = broll["src"]
            if is_image(bsrc):
                cmd += ["-loop", "1", "-framerate", str(self.fps), "-t", f"{d_out:.3f}", "-i", bsrc]
                bz = float(broll.get("zoom", 1.0))
                bz2 = float(broll.get("zoom_to", bz + 0.08))
                b0, b1 = 0.0, 0.0
            else:
                b0 = float(broll.get("start", 0.0))
                b1 = b0 + d_out
                cmd += ["-stream_loop", "-1", "-ss", f"{b0:.3f}", "-t", f"{d_out:.3f}", "-i", bsrc]
                bz = float(broll.get("zoom", 1.0))
                bz2 = float(broll.get("zoom_to", bz + 0.04))
            vchain = "setpts=PTS-STARTPTS," + self._vchain(bsrc, b0, b1, bz, bz2, broll.get("focus", "face"), d_out,
                                                                broll.get("fit"), 1.0, broll.get("reframe"))
            a_idx = 1
            cmd += ["-ss", f"{seg['start']:.3f}", "-t", f"{d_src:.3f}", "-i", src]
        else:
            if is_image(src):
                cmd += ["-loop", "1", "-framerate", str(self.fps), "-t", f"{d_out:.3f}", "-i", src]
            else:
                cmd += ["-ss", f"{seg['start']:.3f}", "-t", f"{d_src:.3f}", "-i", src]
            pts = f"setpts=(PTS-STARTPTS)/{speed}" if speed != 1.0 else "setpts=PTS-STARTPTS"
            vchain = pts + "," + self._vchain(src, seg["start"], seg["end"], zoom, zoom_to, seg.get("focus", "face"),
                                              d_out, seg.get("fit"), speed, seg.get("reframe"))
            a_idx = 0
        vchain += ",tpad=stop_mode=clone:stop_duration=0.2"  # cobre o meio quadro do arredondamento
        use_src_audio = self.plan.get("audio", "source") == "source" and not is_image(src) \
            and self.info(src)["has_audio"]
        if use_src_audio:
            achain = "asetpts=PTS-STARTPTS"
            if speed != 1.0:
                achain += "," + _atempo(speed)
            fo = max(0.0, d_out - 0.015)
            achain += f",aresample=48000,aformat=channel_layouts=stereo,afade=t=in:d=0.012," \
                      f"afade=t=out:st={fo:.3f}:d=0.015,apad"
            fc = f"[0:v]{vchain}[v];[{a_idx}:a]{achain}[a]"
        else:
            cmd += ["-f", "lavfi", "-t", f"{d_out:.6f}", "-i", "anullsrc=r=48000:cl=stereo"]
            n_in = 2 if broll else 1
            fc = f"[0:v]{vchain}[v];[{n_in}:a]anull[a]"
        cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{d_out:.6f}",
                "-c:v", "libx264", "-preset", self.preset, "-crf", str(self.crf), "-r", str(self.fps),
                "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(out)]
        run(cmd, verbose=self.verbose)
        return out

    # ------------------------------------------------------------ efeitos sonoros
    def sfx_events(self, words_out: list) -> list:
        """Lista de efeitos com `at` = momento do evento no vídeo final (o ponto de sincronia cai ali)."""
        ev = [dict(e) for e in self.plan.get("sfx") or []]
        auto = self.plan.get("auto_sfx") or {}
        if auto.get("on_zoom"):
            t, prev = 0.0, None
            for seg in self.plan["segments"]:
                z = seg.get("zoom", 1.0)
                if prev is not None and z != prev:
                    ev.append({"at": t, "type": auto["on_zoom"], "auto": True})
                prev = z
                t += seg_out_dur(seg)
        if auto.get("on_emphasis"):
            emph = set((self.plan.get("captions") or {}).get("emphasis") or [])
            for w in words_out:
                if w["i"] in emph:
                    ev.append({"at": w["s"], "type": auto["on_emphasis"], "auto": True})
        if auto.get("on_cut"):
            t = 0.0
            for seg in self.plan["segments"][:-1]:
                t += seg_out_dur(seg)
                ev.append({"at": t, "type": auto["on_cut"], "auto": True})
        # automáticos não empilham: no máximo um efeito a cada 0,12 s (o manual tem prioridade)
        out = [e for e in ev if not e.get("auto")]  # manual nunca é descartado
        for e in sorted((e for e in ev if e.get("auto")), key=lambda e: float(e["at"])):
            if all(abs(float(e["at"]) - float(k["at"])) >= 0.12 for k in out):
                out.append(e)
        return sorted(out, key=lambda e: float(e["at"]))

    # ------------------------------------------------------------ pipeline
    def run(self) -> str:
        segs = self.plan["segments"]
        print(f"[edin] Renderizando {len(segs)} segmentos em {self.W}x{self.H} @ {self.fps:g}fps"
              f"{' (rascunho)' if self.draft else ''}")
        files = []
        for i, seg in enumerate(segs):
            files.append(self.render_segment(i, seg))
            print(f"\r[edin] segmento {i + 1}/{len(segs)}", end="", flush=True)
        print()
        lst = self.wd / "concat.txt"
        lst.write_text("".join(f"file '{f.name}'\n" for f in files))
        joined = self.wd / "joined.mov"
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst.name, "-c", "copy", joined.name],
            cwd=str(self.wd))
        total = sum(seg_out_dur(s) for s in segs)

        words_out = remap_words(self.plan)
        cap = self.plan.get("captions")
        titles = self.plan.get("titles") or []
        has_subs = bool((cap and words_out) or titles)
        if has_subs:
            ass = build_ass(words_out if cap else [], cap or {}, self.W, self.H, titles, total)
            (self.wd / "captions.ass").write_text(ass, encoding="utf-8")

        # 1ª passada, só áudio: voz + SFX + música + loudnorm -> mix.wav. Num filtergraph único com vídeo e
        # áudio, o ffmpeg 8 com encoder AAC abria saltos no áudio (3 s = lookahead do loudnorm): fala sumia.
        voice_src = joined.name
        vcfg = self.plan.get("voice")
        if vcfg and vcfg.get("clean") not in (None, False, "none") and self.plan.get("audio", "source") == "source":
            from .voice import clean as clean_voice

            print(f"[edin] Limpando a voz ({vcfg.get('clean')}, {vcfg.get('chain') or 'sem cadeia'})...")
            voice_src = clean_voice(str(self.wd / joined.name), str(self.wd / "voz_limpa.wav"), vcfg, self.verbose)
        inputs = ["-i", voice_src]
        fc = ["[0:a]asplit=2[voice][sc]"]
        mix = ["[voice]"]
        n = 1
        for k, e in enumerate(self.sfx_events(words_out)):
            f = sfx_file(e["type"], self.cache)
            inputs += ["-i", str(f)]
            ms = int(sync_start(e["type"], float(e["at"])) * 1000)
            vol = float(e.get("volume", SFX_VOLUME.get(e["type"], 0.4)))
            fc.append(f"[{n}:a]adelay={ms}|{ms},volume={vol}[s{k}]")
            mix.append(f"[s{k}]")
            n += 1
        music = self.plan.get("music")
        if music and music.get("file"):
            inputs += ["-stream_loop", "-1", "-ss", str(float(music.get("start", 0))), "-i", music["file"]]
            vol = float(music.get("volume", 0.12))
            fade = max(0.0, total - 1.5)
            fc.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.3f},"
                      f"volume={vol},afade=t=in:d=0.4,afade=t=out:st={fade:.3f}:d=1.5[mus]")
            if music.get("duck", True) and self.plan.get("audio", "source") == "source":
                fc.append("[mus][sc]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[musd]")
                mix.append("[musd]")
            else:
                fc.append("[sc]anullsink")
                mix.append("[mus]")
            n += 1
        else:
            fc.append("[sc]anullsink")
        lufs = float(self.plan.get("loudness", -14))
        fc.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=first,"
                  f"loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000[a]")
        out_abs = str(Path(self.output).resolve())
        run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[a]",
             "-c:a", "pcm_s16le", "mix.wav"], cwd=str(self.wd), verbose=self.verbose)
        # 2ª passada: legenda no vídeo e junta o áudio já mixado
        vf = f"subtitles=captions.ass:fontsdir='{ffmpeg_filter_path(str(FONTS_DIR))}'" if has_subs else "null"
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", joined.name, "-i", "mix.wav", "-filter_complex", f"[0:v]{vf}[v]",
               "-map", "[v]", "-map", "1:a", "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", self.preset,
               "-crf", str(self.crf + 2),
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_abs]
        run(cmd, cwd=str(self.wd), verbose=self.verbose)
        print(f"[edin] Pronto: {out_abs} ({total:.1f}s)")
        return out_abs


def render(plan_path: str, output: str, draft: bool = False, keep: bool = False, verbose: bool = False) -> str:
    plan = load_plan(plan_path)
    r = Renderer(plan, output, draft, verbose)
    try:
        return r.run()
    finally:
        if not keep:
            for f in r.wd.glob("seg_*.mov"):
                f.unlink()
            for name in ("joined.mov", "mix.wav"):
                p = r.wd / name
                if p.exists():
                    p.unlink()


def contact_sheet(video: str, out: str, n: int = 12, cols: int = 4) -> str:
    info = probe(video)
    rows = (n + cols - 1) // cols
    fps = n / max(info["duration"], 0.1)
    run(["ffmpeg", "-y", "-v", "error", "-i", video, "-vf",
         f"fps={fps:.5f},scale=360:-2,drawtext=fontfile='{ffmpeg_filter_path(str(FONTS_DIR / 'Montserrat-ExtraBold.ttf'))}'"
         f":text='%{{pts\\:hms}}':x=8:y=8:fontsize=22:fontcolor=white:"
         f"box=1:boxcolor=black@0.6,tile={cols}x{rows}:padding=6:color=0x222222", "-frames:v", "1", out])
    return out


def clean(output: str) -> None:
    wd = workdir_for(output)
    shutil.rmtree(wd, ignore_errors=True)
