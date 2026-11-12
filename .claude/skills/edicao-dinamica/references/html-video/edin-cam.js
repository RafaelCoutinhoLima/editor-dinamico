/* edin-cam.js: câmera 2.5D por camadas (carregue depois de edin-video.js).
 *
 * Valores e nomes alinhados com references/higgsfield-camera.md:
 *  - data-z = fator de parallax k da camada: fundo 0.25, meio 0.6, sujeito 1, frente 1.5.
 *  - câmera que SE DESLOCA (dolly, truck, crane, arc, drone) tem parallax:
 *      escala da camada = 1 + (S - 1) * k ; deslocamento da camada = (tx, ty) * k
 *  - câmera que GIRA (pan, tilt, zoom de lente) não tem parallax: todas andam e escalam igual.
 *  - tx/ty em % do quadro; positivo = conteúdo vai para a direita/baixo.
 *  - lente = perspectiva CSS: 50 mm = 1480 px numa largura de 1080.
 *  - blur de movimento com obturador 180 graus: comprimento = 0,5 x deslocamento por quadro (máx. 40 px).
 *
 * Uso:
 *   const cam = EdinCam.camera(el, ctx);           // em montar(el, ctx)
 *   const mov = EdinCam.mix([EdinCam.preset('dolly-in'), EdinCam.preset('handheld', { intensidade: 0.5 })]);
 *   cam.aplicar(mov, p, t);                        // em atualizar(el, t, p, ctx)
 * ou só `camera: mov` na cena (o kit aplica sozinho depois de atualizar).
 *
 * Atributos das camadas (filhos de el):
 *   data-z="0.25"     fator de parallax (padrão 1)
 *   data-sobra="0.15" camada maior que o quadro, 15% de cada lado (fundo para pan/orbit/handheld)
 *   data-cobre="0"    desliga a escala de cobertura automática (ligada por padrão em camadas com k < 1)
 *   data-gira="1"     recebe o rotateY do orbit/arc (padrão: só o sujeito, k entre 0,75 e 1,25)
 *   data-giro         gira no próprio eixo no lazy-susan
 *   data-tela         tela de app: nunca amplia além de 1,0, nunca corta, sem rotação nem blur
 *   data-desfoque="6" profundidade de campo fixa da camada (px de design de blur), somada ao foco da câmera
 *
 * Tudo em segundos, nada em quadros: o mesmo vídeo a 30 ou 60 fps tem o mesmo movimento. O blur de
 * movimento é o deslocamento durante o obturador (180 graus = meio intervalo entre quadros), dividido pelos
 * K subquadros quando o edin renderiza com --motion-blur K (?mb=K).
 */
(function () {
  'use strict';
  const EV = window.EdinVideo;
  if (!EV) throw new Error('carregue edin-video.js antes de edin-cam.js');
  const { clamp, lerp, ease, chaves, ruido } = EV;
  const W = EV.w, H = EV.h, FPS = EV.fps, U = EV.u, MB = EV.mb || 1, OBT = EV.obturador || 0.5;
  const RAD = Math.PI / 180;
  const PERSP50 = 1480 * (W / 1080);
  const persp = (pxEm1080) => pxEm1080 * (W / 1080);
  const pega = (e, padrao) => (typeof e === 'function' ? e : (e && ease[e]) || padrao);

  // ------------------------------------------------------------------ estado
  function neutro() {
    return {
      S: 1,          // dolly (com parallax)
      zoom: 1,       // lente (sem parallax)
      tx: 0, ty: 0,  // truck/crane em % do quadro (com parallax)
      px: 0, py: 0,  // pan/tilt em % do quadro (sem parallax)
      rx: 0, ry: 0, rz: 0, // graus, em todas as camadas
      orbita: 0,     // graus: rotateY no sujeito + parallax oposto fundo/frente
      giro: 0,       // graus: lazy-susan, só camadas data-giro
      vertigo: 0,    // dolly-zoom: escala extra 1 + vertigo * (1 - k); sujeito fica igual
      frente: 1,     // escala extra das camadas de frente (k >= 1,2): through-object
      persp: null,   // perspectiva em px (null = 50 mm)
      olhoPeixe: 0,  // 0,2 a 0,4
      obturador: 0.5, blurMax: 40 * U,
      foco: null, abertura: 0, // rack-focus: k em foco e blur máximo em px
      estabiliza: 0, // 0..1: o sujeito (k perto de 1) ignora o movimento (snorricam)
      sujeito: [0, 0], // deslocamento do sujeito em % (head-tracking)
      tempo: 1,      // velocidade do tempo da cena sugerida (bullet-time, hyperlapse)
      opFundo: 1,    // opacidade das camadas de fundo (k < 0,5): a transição travessia some com o fundo de A
      alvo: [0.5, 0.5], _alvo: false,
      ids: [],
    };
  }

  function combinar(estados) {
    const r = neutro();
    let alvoOk = false;
    for (const s of estados) {
      r.S *= s.S; r.zoom *= s.zoom; r.frente *= s.frente; r.tempo *= s.tempo; r.opFundo *= s.opFundo ?? 1;
      for (const k of ['tx', 'ty', 'px', 'py', 'rx', 'ry', 'rz', 'orbita', 'giro', 'vertigo']) r[k] += s[k];
      r.sujeito = [r.sujeito[0] + s.sujeito[0], r.sujeito[1] + s.sujeito[1]];
      if (s.persp != null) r.persp = s.persp;
      if (s.foco != null) r.foco = s.foco;
      r.olhoPeixe = Math.max(r.olhoPeixe, s.olhoPeixe);
      r.obturador = Math.max(r.obturador, s.obturador);
      r.blurMax = Math.max(r.blurMax, s.blurMax);
      r.abertura = Math.max(r.abertura, s.abertura);
      r.estabiliza = Math.max(r.estabiliza, s.estabiliza);
      if (!alvoOk && s._alvo) { r.alvo = s.alvo; r._alvo = true; alvoOk = true; }
      r.ids = r.ids.concat(s.ids);
    }
    return r;
  }

  // ------------------------------------------------------------------ presets
  // f(st, q, o) onde q = progresso já com easing aplicado quando `e` existe;
  // o = { k (intensidade), e (easing), t (s locais do preset), T (s locais da cena), D (duração da cena), opcoes }
  const pc = (pxDesign) => (pxDesign * U / W) * 100; // px de design para % da largura
  const rDur = 0.5;

  const P = {
    'static': { ease: 'suave', f(s, q, o) { s.S = 1 + 0.006 * o.k * o.e(q); } },
    'dolly-in': { ease: 'suave', f(s, q, o) { s.S = 1 + 0.12 * o.k * o.e(q); s.persp = PERSP50; } },
    'dolly-out': { ease: 'suave', f(s, q, o) { s.S = 1 + 0.12 * o.k * (1 - o.e(q)); s.persp = PERSP50; } },
    'super-dolly-in': { ease: 'outExpo', dur: 0.8, f(s, q, o) { s.S = 1 + 0.6 * o.k * o.e(q); } },
    'super-dolly-out': { ease: 'outExpo', dur: 1.0, f(s, q, o) { s.S = 1 + 0.6 * o.k * (1 - o.e(q)); } },
    'double-dolly': {
      ease: 'inOutCubic',
      f(s, q, o) { s.S = 1 + (chaves(q, [[0, 1], [0.4, 1.08, o.e], [0.55, 1.08], [1, 1.25, o.e]]) - 1) * o.k; },
    },
    // anda para frente e abre a lente: sujeito igual, fundo se afasta (1 a 0,78)
    'dolly-zoom-in': { ease: 'inOutCubic', f(s, q, o) { const e = o.e(q); s.vertigo = -0.29 * o.k * e; s.persp = persp(lerp(1200, 700, e)); } },
    // recua e fecha a lente: sujeito igual, fundo cresce atrás (1 a 1,35)
    'dolly-zoom-out': { ease: 'inOutCubic', f(s, q, o) { const e = o.e(q); s.vertigo = 0.47 * o.k * e; s.persp = persp(lerp(1200, 2400, e)); } },
    'crash-zoom-in': {
      ease: 'outExpo', dur: 0.3,
      f(s, q, o) {
        s.zoom = Math.exp(Math.log(1 + 0.8 * o.k) * o.e(q));
        // sacudida de 2 batidas de 1/30 s com 8 px quando para (em segundos: igual a 30 ou 60 fps)
        const qd = Math.floor((o.t - o.dur) * 30 + 1e-6);
        if (qd === 0) s.py = pc(8); else if (qd === 1) s.py = pc(-4);
      },
    },
    'crash-zoom-out': { ease: 'outExpo', dur: 0.32, f(s, q, o) { s.zoom = Math.exp(Math.log(1 + 0.8 * o.k) * (1 - o.e(q))); } },
    'rapid-zoom-in': { ease: 'inOutQuint', dur: 0.65, f(s, q, o) { s.zoom = Math.exp(Math.log(1 + 0.35 * o.k) * o.e(q)); } },
    'yoyo-zoom': {
      ease: 'outCubic', dur: 1.0,
      f(s, q, o) {
        const top = 0.25 * o.k, fimV = 0.03 * o.k;
        s.zoom = q < 0.45 ? 1 + top * o.e(q / 0.45) : 1 + lerp(top, fimV, ease.easeInCubic((q - 0.45) / 0.55));
      },
    },
    'crane-up': { ease: 'suave', f(s, q, o) { const e = o.e(q); s.ty = 18 * o.k * e; s.rx = 8 * o.k * e; s.persp = persp(1200); } },
    'crane-down': { ease: 'suave', f(s, q, o) { const e = o.e(q); s.ty = -18 * o.k * e; s.rx = 8 * o.k * (1 - e); s.persp = persp(1200); } },
    'crane-over': { ease: 'inOutCubic', f(s, q, o) { const e = o.e(q); s.rx = 55 * o.k * e; s.S = 1 + 0.1 * o.k * e; s.ty = -10 * o.k * e; s.persp = persp(2400); } }, // 1200 deixaria o horizonte entrar no quadro a 55 graus
    'tilt-up': { ease: 'suave', f(s, q, o) { const e = o.e(q); s.py = 15 * o.k * e; s.rx = -4 * o.k * e; } },
    'tilt-down': { ease: 'suave', f(s, q, o) { const e = o.e(q); s.py = -15 * o.k * e; s.rx = 4 * o.k * e; } },
    'pan-left': { ease: 'suave', f(s, q, o) { const e = o.e(q); s.px = 20 * o.k * e; s.ry = 4 * o.k * e; } },
    'pan-right': { ease: 'suave', f(s, q, o) { const e = o.e(q); s.px = -20 * o.k * e; s.ry = -4 * o.k * e; } },
    // dentro da cena (para emendar cenas use a transição 'whip-pan' do edin-video)
    'whip-pan': {
      ease: 'inExpo', dur: 0.25,
      f(s, q, o) {
        const d = { esquerda: [-1, 0], direita: [1, 0], cima: [0, -1], baixo: [0, 1] }[o.opcoes.direcao || 'esquerda'];
        const e = o.e(q);
        s.px = d[0] * 100 * o.k * e; s.py = d[1] * 100 * o.k * e; s.blurMax = 80 * U;
      },
    },
    // 2.5D aguenta bem até ~35 graus; volta inteira só com sujeito de duas faces (backface-visibility)
    'orbit-360': { ease: 'linear', f(s, q, o) { s.orbita = 360 * o.k * o.e(q); } },
    'arc-left': { ease: 'suave', f(s, q, o) { s.orbita = 30 * o.k * o.e(q); s.persp = persp(1200); } },
    'arc-right': { ease: 'suave', f(s, q, o) { s.orbita = -30 * o.k * o.e(q); s.persp = persp(1200); } },
    'lazy-susan': { ease: 'linear', f(s, q, o) { s.giro = 360 * o.k * o.e(q); } },
    'bullet-time': {
      ease: 'suave',
      f(s, q, o) {
        s.orbita = lerp(-20, 20, o.e(q)) * o.k; s.persp = persp(1200);
        s.tempo = tempoBullet(o.T, o.D);
      },
    },
    'robo-arm': {
      ease: 'inOutQuint',
      f(s, q, o) {
        const v = chaves(q, [
          [0, [1, 0, 0, 0, 0]],
          [0.3, [1.08, -6, 0, 0, 12], o.e], [0.38, [1.08, -6, 0, 0, 12]],
          [0.68, [1.15, 4, -5, -8, -6], o.e], [0.76, [1.15, 4, -5, -8, -6]],
          [1, [1.2, 0, 0, 0, 0], o.e],
        ]);
        s.S = 1 + (v[0] - 1) * o.k; s.tx = v[1] * o.k; s.ty = v[2] * o.k; s.rx = v[3] * o.k; s.ry = v[4] * o.k;
        s.persp = persp(1200);
      },
    },
    'fpv-drone': {
      ease: EV.bezier(0.3, 0.05, 0.7, 0.95),
      f(s, q, o) {
        const T = o.T;
        s.S = 1 + 1.4 * o.k * o.e(q);
        s.rz = 8 * o.k * Math.sin(2 * Math.PI * 0.35 * T);
        s.ty = 1.5 * o.k * Math.sin(2 * Math.PI * 1.5 * T);
        s.tx = 6 * o.k * Math.sin(2 * Math.PI * 0.22 * T + 0.6);
        s.persp = persp(1000);
      },
    },
    'aerial-pullback': {
      ease: 'outCubic',
      f(s, q, o) { const e = o.e(q); s.S = 1 + 0.5 * o.k * (1 - e); s.ty = -12 * o.k * e; s.rx = 30 * o.k * e; s.persp = persp(1200); },
    },
    'fisheye': { ease: 'linear', f(s, q, o) { s.olhoPeixe = 0.3 * o.k; s.persp = persp(500); s.zoom = 1.1; } },
    'handheld': {
      ease: 'linear',
      f(s, q, o) {
        const n = ruido(o.opcoes.semente || 11);
        const T = o.T;
        s.tx = pc((6 * n.fbm(0.8 * T) + 1 * n.n(7 * T + 40)) * o.k);
        s.ty = (((6 * n.fbm(0.8 * T + 100) + 1 * n.n(7 * T + 140)) * o.k) * U / H) * 100;
        s.rz = 0.4 * o.k * n.n(0.8 * T + 300);
      },
    },
    'snorricam': {
      ease: 'linear',
      f(s, q, o) {
        const n = ruido(o.opcoes.semente || 23), T = o.T;
        s.estabiliza = 1;
        s.rz = 6 * o.k * n.fbm(0.65 * T);
        s.tx = 6 * o.k * n.fbm(0.65 * T + 50);
        s.ty = 3 * o.k * n.fbm(0.65 * T + 90);
      },
    },
    'head-tracking': {
      ease: 'linear',
      f(s, q, o) {
        // o sujeito anda; a câmera segue com atraso (pos += (alvo - pos) * 0,25 a cada 1/30 s, em passo fixo
        // de 1/120 s: o mesmo atraso a 30 ou 60 fps)
        const traj = o.opcoes.trajeto || ((T) => [4 * o.k * Math.sin(2 * Math.PI * 0.3 * T), 3 * o.k * Math.sin(2 * Math.PI * 0.45 * T + 1)]);
        const PASSO = 1 / 120, g = 1 - Math.pow(0.75, 30 * PASSO);
        const n = Math.max(0, Math.floor(o.T / PASSO + 1e-9));
        let c = traj(0);
        for (let i = 1; i <= n; i++) { const a = traj(i * PASSO); c = [c[0] + (a[0] - c[0]) * g, c[1] + (a[1] - c[1]) * g]; }
        const a = traj(o.T), fr = o.T / PASSO - n;
        c = [c[0] + (a[0] - c[0]) * g * fr, c[1] + (a[1] - c[1]) * g * fr];
        s.tx = -c[0]; s.ty = -c[1];
        s.sujeito = [a[0], a[1]];
      },
    },
    'through-object': {
      ease: 'inExpo', dur: 0.8,
      f(s, q, o) { const e = o.e(q); s.frente = Math.exp(Math.log(1 + 5 * o.k) * e); s.S = 1 + 0.15 * o.k * e; },
    },
    'hyperlapse': {
      ease: 'linear',
      f(s, q, o) {
        // tempo em degraus de 1/15 s (2 quadros a 30 fps, 4 a 60 fps)
        const passo = 2 / 30, Tq = Math.floor(o.T / passo + 1e-6) * passo;
        const qq = o.D ? clamp(Tq / o.D) : q;
        s.S = 1 + 1.6 * o.k * qq;
        const n = ruido(31);
        s.tx = pc(3 * n.n(1.1 * Tq)); s.rz = 0.2 * n.n(0.9 * Tq + 7);
        s.tempo = 8;
      },
    },
    'rack-focus': {
      ease: 'inOutCubic',
      f(s, q, o) {
        const e = o.e(q);
        s.foco = lerp(o.opcoes.focoDe ?? 1.5, o.opcoes.focoPara ?? 0.25, e);
        s.abertura = 8 * o.k * U; s.S = 1 + 0.02 * e;
      },
    },
    // deriva: a câmera nunca para. Respiração (escala de 1 a 1 - 1,2%, nunca amplia: serve em tela de app),
    // deriva lenta com parallax (ruído de ~0,12 Hz, ±1,2% do quadro) e roll de ±0,25 grau. Opções:
    // `zeroNoInicio` (posição neutra exata no t=0: capa e loop), `entrada`/`saida` (s de rampa da amplitude;
    // `saida` termina neutro exato no fim da cena), `semente`.
    'deriva': {
      ease: 'linear',
      f(s, q, o) {
        const n = ruido(o.opcoes.semente || 3), T = o.T, op = o.opcoes;
        let env = 1;
        if (op.entrada) env *= ease.smoothstep(T / op.entrada);
        if (op.saida && o.D) env *= ease.smoothstep((o.D - T) / op.saida);
        const z = op.zeroNoInicio ? 1 : 0;
        const a = o.k * env;
        s.S = 1 - 0.012 * a * (1 - Math.cos((2 * Math.PI * T) / 7)) / 2;
        s.tx = 1.2 * a * (n.fbm(0.12 * T) - z * n.fbm(0));
        s.ty = 0.8 * a * (n.fbm(0.1 * T + 40) - z * n.fbm(40));
        s.rz = 0.25 * a * (n.n(0.09 * T + 9.5) - z * n.n(9.5));
        s.persp = PERSP50;
      },
    },
    // foco: profundidade de campo da cena. `foco` = k da camada nítida (1 = sujeito), `abertura` = blur máximo
    // em px de design (padrão 6) nas camadas longe dele; com `focoPara` e `inicio`/`duracao` (ou de/ate)
    // vira rack focus.
    'foco': {
      ease: 'inOutCubic',
      f(s, q, o) {
        const de = o.opcoes.foco ?? 1, para = o.opcoes.focoPara ?? de;
        s.foco = lerp(de, para, o.e(q)); s.abertura = (o.opcoes.abertura ?? 6) * o.k * U;
        if (para !== de) s.S = 1 + 0.015 * Math.sin(Math.PI * o.e(q)); // respiração da lente no rack
      },
    },
    'low-shutter': {
      ease: 'linear',
      f(s, q, o) {
        const n = ruido(o.opcoes.semente || 41), T = o.T;
        s.obturador = 1.0; s.blurMax = 60 * U;
        s.tx = pc(14 * o.k * n.fbm(0.9 * T)); s.ty = ((14 * o.k * n.fbm(0.9 * T + 70) * U) / H) * 100;
        s.rz = 1.2 * o.k * n.n(0.7 * T + 5);
      },
    },
  };

  // rampa do bullet-time: 1 -> 0,1x em 0,2 s (outExpo) e volta nos últimos 0,2 s (inExpo)
  function tempoBullet(T, D) {
    const r = 0.2;
    let v = 1 - 0.9 * ease.outExpo(T / r);
    if (D) v = lerp(v, 1, ease.inExpo((T - (D - r)) / r));
    return v;
  }
  // tempo deformado (integral da velocidade): use na ação da cena durante bullet-time
  function tempoDeformado(T, D) {
    const h = 1 / 240; let s = 0;
    for (let x = 0; x < T; x += h) s += tempoBullet(Math.min(T, x + h / 2), D) * Math.min(h, T - x);
    return s;
  }

  const IDS = Object.keys(P);

  function preset(id, opcoes = {}) {
    const def = P[id];
    if (!def) throw new Error(`preset de câmera desconhecido: ${id}. Existem: ${IDS.join(', ')}`);
    const k = opcoes.intensidade ?? 1;
    const e = pega(opcoes.easing, pega(def.ease, ease.linear));
    const porTempo = opcoes.inicio != null || opcoes.duracao != null || (def.dur && opcoes.de == null && opcoes.ate == null);
    const ini = opcoes.inicio || 0, dur = opcoes.duracao || def.dur || 1;
    const f = function (p, T, D) {
      if (T == null) T = p * (D || opcoes.duracaoCena || 3);
      let q;
      if (porTempo) q = clamp((T - ini) / dur);
      else q = clamp((p - (opcoes.de ?? 0)) / (((opcoes.ate ?? 1) - (opcoes.de ?? 0)) || 1));
      const st = neutro();
      def.f(st, q, { k, e, t: T - ini, dur, T, D, opcoes });
      if (opcoes.alvo) { st.alvo = opcoes.alvo; st._alvo = true; }
      st.ids = [id];
      return st;
    };
    f.id = id;
    if (id === 'bullet-time') f.tempoDeformado = tempoDeformado;
    return f;
  }

  function mix(lista) {
    const fs = lista.map((x) => (typeof x === 'string' ? preset(x) : x));
    const f = (p, T, D) => combinar(fs.map((g) => g(p, T, D)));
    f.id = fs.map((g) => g.id).join('+');
    return f;
  }

  // ------------------------------------------------------------------ mapa de olho de peixe
  let _mapaPeixe = null;
  function mapaPeixe() {
    if (_mapaPeixe) return _mapaPeixe;
    const n = 256, c = document.createElement('canvas'); c.width = c.height = n;
    const x = c.getContext('2d'), d = x.createImageData(n, n);
    for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
      const u = (i / (n - 1)) * 2 - 1, v = (j / (n - 1)) * 2 - 1, r2 = u * u + v * v, k = (j * n + i) * 4;
      d.data[k] = 128 + 127 * clamp(-u * r2 * 0.5, -1, 1);
      d.data[k + 1] = 128 + 127 * clamp(-v * r2 * 0.5, -1, 1);
      d.data[k + 2] = 128; d.data[k + 3] = 255;
    }
    x.putImageData(d, 0, 0);
    return (_mapaPeixe = c.toDataURL());
  }

  // ------------------------------------------------------------------ câmera
  let _idc = 0;
  function camera(root, ctx = {}) {
    const NS = 'http://www.w3.org/2000/svg';
    const defs = ctx.defs || EV.svgDefs(root);
    const D = ctx.duracao || 3;
    const avisados = new Set();
    const avisar = (m) => { if (!avisados.has(m)) { avisados.add(m); console.warn(`[edin-cam] ${m}`); } };

    const todas = [...root.querySelectorAll('[data-z],[data-tela]')];
    const camadas = todas.filter((el) => { let a = el.parentElement; while (a && a !== root) { if (todas.includes(a)) return false; a = a.parentElement; } return true; })
      .map((el) => {
        el.classList.add('edin-camada');
        const k = el.hasAttribute('data-z') ? parseFloat(el.getAttribute('data-z')) : 1;
        const sobra = parseFloat(el.getAttribute('data-sobra') || '0');
        if (sobra > 0) { el.style.inset = `${-sobra * 100}%`; }
        const tela = el.hasAttribute('data-tela');
        const cobreAttr = el.getAttribute('data-cobre');
        return {
          el, k, tela, sobra, desfoque: parseFloat(el.getAttribute('data-desfoque') || '0') * U,
          gira: el.hasAttribute('data-gira') ? parseFloat(el.getAttribute('data-gira') || '1') : (Math.abs(k - 1) <= 0.25 ? 1 : 0),
          giro: el.hasAttribute('data-giro'),
          cobre: !tela && (cobreAttr != null ? cobreAttr !== '0' : k < 1),
          blur: EV.filtroBlur(defs, el),
          conteudo: tela ? (el.querySelector('[data-tela-conteudo]') || (el.children.length === 1 ? el.children[0] : el)) : null,
        };
      });
    const temGiro = camadas.some((c) => c.giro);
    const temTela = camadas.some((c) => c.tela);
    if (!camadas.length) avisar(`${ctx.id || 'cena'}: nenhuma camada [data-z] dentro da câmera`);

    // filtro de olho de peixe (aplicado no root; se houver tela de app, só nas outras camadas)
    let peixe = null;
    function filtroPeixe() {
      if (peixe) return peixe;
      const id = `edin-peixe-${++_idc}`;
      const f = document.createElementNS(NS, 'filter');
      f.setAttribute('id', id); f.setAttribute('x', '0'); f.setAttribute('y', '0'); f.setAttribute('width', '100%'); f.setAttribute('height', '100%');
      f.setAttribute('color-interpolation-filters', 'sRGB');
      const im = document.createElementNS(NS, 'feImage');
      im.setAttribute('href', mapaPeixe()); im.setAttribute('preserveAspectRatio', 'none');
      im.setAttribute('x', '0'); im.setAttribute('y', '0'); im.setAttribute('width', '100%'); im.setAttribute('height', '100%'); im.setAttribute('result', 'm');
      const dm = document.createElementNS(NS, 'feDisplacementMap');
      dm.setAttribute('in', 'SourceGraphic'); dm.setAttribute('in2', 'm'); dm.setAttribute('xChannelSelector', 'R'); dm.setAttribute('yChannelSelector', 'G');
      f.appendChild(im); f.appendChild(dm); defs.appendChild(f);
      return (peixe = { id, dm });
    }

    let geo = null; // geometria das camadas (medida uma vez, layout estático)
    function medir() {
      geo = camadas.map((c) => ({ x: c.el.offsetLeft, y: c.el.offsetTop, w: c.el.offsetWidth || W, h: c.el.offsetHeight || H }));
    }

    function calc(st, c) {
      const k = c.k;
      let s = (1 + (st.S - 1) * k) * st.zoom * (1 + st.vertigo * (1 - k));
      let op = k < 0.5 ? st.opFundo : 1;
      if (k >= 1.2) {
        s *= st.frente;
        const sd = (1 + (st.S - 1) * k) * st.frente;
        if (sd > 3) op = clamp((4.5 - sd) / 1.5); // passou da câmera
      }
      let tx = ((st.tx * k + st.px) / 100) * W, ty = ((st.ty * k + st.py) / 100) * H;
      const so = Math.sin(st.orbita * RAD);
      if (k < 1) tx += (32 * (1 - k) * so / 100) * W; else tx -= (80 * (k - 1) * so / 100) * W;
      const prox = Math.max(0, 1 - Math.abs(k - 1) / 0.3);
      tx += (st.sujeito[0] / 100) * W * prox; ty += (st.sujeito[1] / 100) * H * prox;
      let rx = st.rx, ry = st.ry + st.orbita * c.gira, rz = st.rz;
      if (c.giro || (!temGiro && Math.abs(k - 1) < 0.05)) ry += st.giro;
      const w = prox * st.estabiliza;
      if (w) { tx *= 1 - w; ty *= 1 - w; rz *= 1 - w; rx *= 1 - w; }
      return { s, tx, ty, rx, ry, rz, op };
    }

    function cobertura(L, g, O, Pp) {
      // menor escala que mantém a camada cobrindo o quadro (aproximação)
      const ox = O[0], oy = O[1];
      let sT = 1;
      const lados = [
        [ox + L.tx, ox - g.x], [W - ox - L.tx, g.x + g.w - ox],
        [oy + L.ty, oy - g.y], [H - oy - L.ty, g.y + g.h - oy],
      ];
      for (const [need, have] of lados) if (have > 1) sT = Math.max(sT, need / have);
      // rotateX/Y com perspectiva: a borda que se afasta encolhe; resolve a escala exata para ela alcançar a borda do quadro
      const borda = (dist, ext, ang) => {
        if (ang < 1e-4) return 0;
        const den = ext * (Pp * Math.cos(ang) - dist * Math.sin(ang));
        return den > 0 ? (dist * Pp) / den : 4;
      };
      const ax = Math.abs(L.rx * RAD), ay = Math.abs(L.ry * RAD), az = Math.abs(L.rz * RAD);
      const sX = borda(Math.max(oy, H - oy) + Math.abs(L.ty), Math.min(oy - g.y, g.y + g.h - oy), ax);
      const sY = borda(Math.max(ox, W - ox) + Math.abs(L.tx), Math.min(ox - g.x, g.x + g.w - ox), ay);
      const m = Math.cos(az) + (Math.max(W, H) / Math.min(W, H)) * Math.sin(az);
      return Math.min(4, Math.max(sT, sX, sY) * m * 1.004);
    }

    function rectRel(el) {
      const rr = root.getBoundingClientRect(), r = el.getBoundingClientRect(), s = rr.width / W || 1;
      return { x: (r.left - rr.left) / s, y: (r.top - rr.top) / s, w: r.width / s, h: r.height / s };
    }

    const api = {
      camadas,
      estado: null,
      aplicar(mov, p, T) {
        if (!geo) medir();
        const avalia = (pp, tt) => (typeof mov === 'function' ? mov(pp, tt, D) : Object.assign(neutro(), mov || {}));
        const st = avalia(p, T);
        // estados meio obturador antes e depois: o blur é o deslocamento durante o obturador
        const h = (OBT / 2) / FPS;
        const st0 = typeof mov === 'function' ? avalia(clamp(p - h / D), T - h) : st;
        const st1 = typeof mov === 'function' ? avalia(clamp(p + h / D), T + h) : st;
        const Pp = st.persp || PERSP50;
        const O = [st.alvo[0] * W, st.alvo[1] * H];
        const meiaDiag = Math.hypot(W, H) / 2;
        const nome = st.ids.join('+') || 'câmera';
        api.estado = st;

        camadas.forEach((c, i) => {
          const g = geo[i];
          let L = calc(st, c);
          const L0 = calc(st0, c), L1 = calc(st1, c);
          const el = c.el;
          el.style.transformOrigin = `${O[0] - g.x}px ${O[1] - g.y}px`;
          if (c.tela) {
            // ---- regra de Rafael: tela de app inteira, sem ampliar, sem cortar
            if (L.s > 1.001) avisar(`${nome} tentou ampliar a tela de app (${L.s.toFixed(3)}x); limitada a 1,0`);
            if (Math.max(Math.abs(L.rx), Math.abs(L.ry), Math.abs(L.rz)) > 0.5) avisar(`${nome} tentou girar a tela de app; rotação ignorada`);
            const s = Math.min(1, L.s);
            el.style.transform = 'none';
            const R = rectRel(c.conteudo);
            if (R.w > W + 0.5 || R.h > H + 0.5) avisar(`tela de app maior que o quadro (${Math.round(R.w)}x${Math.round(R.h)}); reduza a largura para no máximo ${W}px`);
            let tx = L.tx, ty = L.ty;
            const x0 = O[0] + (R.x - O[0]) * s + tx, x1 = O[0] + (R.x + R.w - O[0]) * s + tx;
            const y0 = O[1] + (R.y - O[1]) * s + ty, y1 = O[1] + (R.y + R.h - O[1]) * s + ty;
            let cx = 0, cy = 0;
            if (x1 - x0 > W) cx = (W - (x0 + x1)) / 2; else if (x0 < 0) cx = -x0; else if (x1 > W) cx = W - x1;
            if (y1 - y0 > H) cy = (H - (y0 + y1)) / 2; else if (y0 < 0) cy = -y0; else if (y1 > H) cy = H - y1;
            if (Math.abs(cx) > 0.5 || Math.abs(cy) > 0.5) avisar(`${nome} tentou cortar a tela de app (empurrava ${Math.round(Math.hypot(cx, cy))} px para fora); posição limitada`);
            tx += cx; ty += cy;
            el.style.transform = `translate(${tx.toFixed(2)}px, ${ty.toFixed(2)}px) scale(${s.toFixed(5)})`;
            el.style.filter = '';
            el.style.opacity = '';
            return;
          }
          if (c.cobre) L.s = Math.max(L.s, cobertura(L, g, O, Pp));
          el.style.transform =
            `translate(${L.tx.toFixed(2)}px, ${L.ty.toFixed(2)}px) perspective(${Pp.toFixed(0)}px) ` +
            `rotateX(${L.rx.toFixed(3)}deg) rotateY(${L.ry.toFixed(3)}deg) rotateZ(${(-L.rz).toFixed(3)}deg) scale(${L.s.toFixed(5)})`;
          el.style.opacity = L.op < 1 ? L.op.toFixed(4) : '';
          if (L.op <= 0.001) el.style.visibility = 'hidden'; else el.style.visibility = '';
          // ---- blur de movimento (pelo deslocamento entre meio quadro antes e depois) + foco
          // L1 - L0 = deslocamento durante o obturador de 180 graus; `obturador` 1 (low-shutter) dobra.
          // Com --motion-blur K cada subtempo cobre 1/K do obturador.
          const ob = (st.obturador / 0.5) / MB, bm = st.blurMax;
          const lx = Math.min(bm, ob * Math.abs(L1.tx - L0.tx)), ly = Math.min(bm, ob * Math.abs(L1.ty - L0.ty));
          const rad = Math.min(bm, (ob * Math.abs(L1.s - L0.s) / Math.max(0.01, L.s)) * meiaDiag) / 3;
          let dof = c.desfoque;
          if (st.abertura > 0 && st.foco != null) dof += Math.min(st.abertura, (st.abertura * Math.abs(c.k - st.foco)) / 0.6);
          const sx = (lx / 2 + rad + dof) / L.s, sy = (ly / 2 + rad + dof) / L.s;
          el.style.filter = c.blur.valor(sx, sy);
        });

        // ---- olho de peixe
        if (st.olhoPeixe > 0.01) {
          const f = filtroPeixe();
          f.dm.setAttribute('scale', String(st.olhoPeixe * Math.min(W, H) * 0.6));
          if (temTela) {
            avisar(`${nome}: olho de peixe não é aplicado na tela de app`);
            camadas.forEach((c) => { if (!c.tela) c.el.style.filter = `${c.el.style.filter || ''} url(#${f.id})`.trim(); });
          } else root.style.filter = `url(#${f.id})`;
        } else if (peixe) root.style.filter = '';
        return st;
      },
    };
    return api;
  }

  window.EdinCam = { camera, preset, mix, neutro, combinar, ids: IDS, tempoDeformado, presets: P };
})();
