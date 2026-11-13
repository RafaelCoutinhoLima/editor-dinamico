/* edin-foto3d.js: foto com parallax real pela profundidade, em WebGL 2 (carregue depois de edin-video.js e
 * edin-cam.js).
 *
 * A foto vira um relevo: cada pixel fica na distância que o mapa de profundidade diz (Depth Anything V2, gerado
 * pelo `edin profundidade foto.png`) e uma câmera 3D de verdade anda na frente dele. Os presets do Higgsfield do
 * edin-cam (dolly, truck, crane, arc/orbit, dolly-zoom, push, zoom, deriva, handheld) chegam aqui como o mesmo
 * estado de câmera das camadas CSS e viram posição, rotação e lente da câmera 3D:
 *   S (dolly)    -> a câmera anda até o alvo (o sujeito escala S; o fundo, menos: parallax pela distância)
 *   tx/ty        -> a câmera desliza de lado (o sujeito anda tx% do quadro; o fundo, menos; a frente, mais)
 *   orbita, rx/ry-> a câmera gira em volta do alvo (arc), reduzida por `orbita` (padrão 0,12: 30 graus viram 3,6)
 *   vertigo      -> dolly-zoom de verdade (anda e compensa a lente; o sujeito fica, o fundo muda), x `vertigo`
 *   zoom, px/py, rz -> lente, pan/tilt e roll (sem parallax, no plano da imagem)
 * Tudo é função do estado da câmera e de t: determinístico (o mesmo quadro em qualquer ordem e com qualquer
 * número de workers).
 *
 * Como desenha: para cada pixel do quadro, um raio sai da câmera e anda pelo relevo (busca linear em disparidade
 * + refinamento binário) até bater na superfície. São duas superfícies: a FRENTE (foto e profundidade
 * originais) e o FUNDO (foto com as bordas de oclusão preenchidas e profundidade sem os degraus, feitas pelo
 * `edin profundidade`). Onde a frente estica (a parede de um degrau de profundidade, que seria a "borracha"),
 * o pixel vem do fundo: atrás do ombro aparece parede/céu, não um rasgo nem um esticão. Câmera parada = a foto
 * original, pixel a pixel. A câmera se afasta da borda sozinha (cobertura): nunca aparece fora da foto.
 *
 * Uso:
 *   <script src="edin-video.js"></script><script src="edin-cam.js"></script><script src="edin-foto3d.js"></script>
 *   <script src="fotos/janela.foto3d.js"></script>       <!-- gerado pelo edin profundidade (imagens embutidas) -->
 *   v.cena({ duracao: 4, camera: EdinCam.mix([EdinCam.preset('dolly-in'), EdinCam.preset('deriva')]),
 *     montar(el, ctx) {
 *       el.innerHTML = `<div data-z="1" data-foto3d></div>`;
 *       this.foto = EdinFoto3D.criar(el.querySelector('[data-foto3d]'), { foto: 'janela', rim: true }, ctx);
 *     },
 *   });
 *
 * Opções de criar(el, op, ctx):
 *   foto       nome registrado pelo .foto3d.js (window.EDIN_FOTOS[nome]) ou { cor, fundo, prof, meta } com URLs
 *   forca      0,6   quanto a profundidade separa os planos (disparidade: 1 + forca * (d - foco)); 0 = foto chapada
 *   foco       'auto' profundidade (0 longe a 1 perto) que fica no lugar no arc/dolly-zoom e nítida no desfoque;
 *                    auto = o sujeito medido pelo edin profundidade
 *   orbita     0,12  fator do orbit/arc (o 2.5D do CSS aguenta 30 graus, uma foto aguenta ~4)
 *   giro       0,25  fator do rx/ry dos presets (crane, tilt) aplicados como giro em volta do alvo
 *   vertigo    0,35  fator do dolly-zoom
 *   abertura   0     profundidade de campo em px de design (6 a 14 é filme); foco em `foco`
 *   rim        false true ou { cor: '#ffd9b0', intensidade: 0.5, de: 'direita'|'esquerda'|'cima'|graus, largura: 7 }
 *              luz de recorte na borda do sujeito do lado da luz (contraluz)
 *   flare      null  { x, y (0..1 na foto, onde está a fonte de luz), cor: '#ffc68a', intensidade: 0.5 }:
 *              brilho + risco anamórfico + fantasmas; anda com o fundo e some atrás do sujeito
 *   vida       true  respiração: escala local de ~0,6% no tronco (região perto do foco), 4,2 s por ciclo;
 *              false ou { amp, periodo, centro: [x, y], raio }
 *   grao       0.035 grão de película próprio da foto (30 Hz, determinístico pelo número do quadro)
 *   passos     auto  passos da busca do raio (auto pelo tamanho do parallax no quadro)
 * Devolve { el, canvas, pronto (Promise), meta, desenhar(estado, T) }. A câmera do edin-cam chama desenhar
 * sozinha; poeira na frente: EdinVideo.poeira(el, { z: 1.7, ... }) como camada normal por cima.
 */
(function () {
  'use strict';
  const EV = window.EdinVideo;
  if (!EV) throw new Error('carregue edin-video.js antes de edin-foto3d.js');
  const { clamp, lerp } = EV;
  const W = EV.w, H = EV.h, U = EV.u, FPS = EV.fps;
  const FOTOS = (window.EDIN_FOTOS = window.EDIN_FOTOS || {});
  const RAD = Math.PI / 180;
  // lente: 40 graus no lado menor do quadro (~50 mm equivalente no vertical)
  const F_CURTO = 1 / Math.tan(20 * RAD);
  const FX = F_CURTO * Math.min(W, H) / W, FY = F_CURTO * Math.min(W, H) / H;

  // ------------------------------------------------------------------ shaders
  const VS = `#version 300 es
  in vec2 p; out vec2 vN;
  void main() { vN = p; gl_Position = vec4(p, 0.0, 1.0); }`;

  const FS_CENA = `#version 300 es
  precision highp float;
  in vec2 vN;
  uniform sampler2D tCor, tFundo, tProf;
  uniform mat3 uRc;      // orientação da câmera (câmera -> mundo)
  uniform vec3 uC;       // posição da câmera
  uniform vec2 uF;       // focal efetiva (x, y)
  uniform vec2 uF0;      // focal neutra
  uniform mat2 uPA; uniform vec2 uPB; // NDC do quadro -> NDC antes do pós (zoom, roll, pan, cobertura)
  uniform vec2 uS;       // recorte da foto no quadro (cover)
  uniform float uA, uDf; // força e foco (disparidade 1 + A (d - Df))
  uniform int uN, uNb;
  uniform vec4 uVida;    // centro (uv), raio, amplitude do instante
  uniform float uAsp;    // altura/largura da foto
  out vec4 o;

  float wDe(float d) { return 1.0 + uA * (d - uDf); }
  vec2 uvDe(vec3 X) {
    float Z = -X.z;
    vec2 n = vec2(uF0.x * X.x / Z, uF0.y * X.y / Z);
    return vec2(0.5 + n.x * 0.5 * uS.x, 0.5 - n.y * 0.5 * uS.y);
  }
  float prof(vec2 uv, int c) { vec4 t = texture(tProf, uv); return c == 0 ? t.r : t.g; }

  // anda o raio em disparidade (perto -> longe) até passar a superfície; refina por bisseção
  vec3 marcha(vec3 ro, vec3 rd, int c, int N) {
    float wMax = wDe(1.0) + 0.002, wMin = wDe(0.0) - 0.002;
    float a = wMax, b = wMin;
    vec2 uv = vec2(0.5);
    bool achou = false;
    for (int i = 0; i <= 96; i++) {
      if (i > N) break;
      float wr = mix(wMax, wMin, float(i) / float(N));
      vec3 X = ro + rd * ((-1.0 / wr - ro.z) / rd.z);
      uv = uvDe(X);
      if (wr <= wDe(prof(uv, c))) { b = wr; achou = true; break; }
      a = wr;
    }
    if (!achou) b = wMin;
    for (int k = 0; k < 7; k++) {
      float m = 0.5 * (a + b);
      vec3 X = ro + rd * ((-1.0 / m - ro.z) / rd.z);
      vec2 u2 = uvDe(X);
      if (m <= wDe(prof(u2, c))) b = m; else a = m;
    }
    vec3 X = ro + rd * ((-1.0 / b - ro.z) / rd.z);
    uv = uvDe(X);
    return vec3(uv, prof(uv, c));
  }

  void main() {
    vec2 n = uPA * vN + uPB;
    vec3 dc = vec3(n.x / uF.x, n.y / uF.y, -1.0);
    vec3 rd = uRc * dc, ro = uC;
    vec3 hf = marcha(ro, rd, 0, uN);
    vec3 hb = marcha(ro, rd, 1, uNb);
    // esticamento da frente (área de textura por pixel) contra um plano liso na profundidade do foco, que a
    // câmera vê sem esticar: parede de degrau (a "borracha") -> fundo
    float wf = wDe(uDf);
    vec2 up = uvDe(ro + rd * ((-1.0 / wf - ro.z) / rd.z));
    vec2 fx = dFdx(hf.xy), fy = dFdy(hf.xy), px_ = dFdx(up), py_ = dFdy(up);
    float aF = abs(fx.x * fy.y - fx.y * fy.x), aP = abs(px_.x * py_.y - px_.y * py_.x);
    float r = sqrt(aF / max(aP, 1e-16));
    float al = smoothstep(0.42, 0.78, r);
    vec2 uvC = hf.xy;
    if (uVida.w != 0.0) {
      vec2 q = (hf.xy - uVida.xy) * vec2(1.0, uAsp);
      float g = exp(-dot(q, q) / (2.0 * uVida.z * uVida.z)) * smoothstep(uDf - 0.28, uDf - 0.08, hf.z);
      uvC = uVida.xy + (hf.xy - uVida.xy) * (1.0 - uVida.w * g);
    }
    vec3 cf = texture(tCor, uvC).rgb, cb = texture(tFundo, hb.xy).rgb;
    o = vec4(mix(cb, cf, al), mix(hb.z, hf.z, al));
  }`;

  const FS_POS = `#version 300 es
  precision highp float;
  uniform sampler2D tCena;
  uniform vec2 uRes;
  uniform float uAb, uFocoD;        // abertura (px do alvo) e profundidade em foco
  uniform vec3 uRimCor; uniform float uRim, uRimR; uniform vec2 uLuz;
  uniform vec4 uFl; uniform vec3 uFlCor; // flare: posição (px), intensidade, raio base (px)
  uniform float uGrao, uQ;
  out vec4 o;
  // hash inteiro (o fract(sin) perde precisão na GPU e desenha hachuras)
  float h(uvec3 v) {
    v = v * 1664525u + 1013904223u;
    v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
    v ^= v >> 16u;
    v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
    return float(v.x & 0xffffffu) / 16777215.0;
  }
  // zona nítida de ±0,1 em volta do foco (o sujeito tem volume: nariz e costas não podem desfocar)
  float coc(float d) { return uAb * clamp((abs(d - uFocoD) - 0.1) / 0.35, 0.0, 1.0); }
  void main() {
    vec2 px = gl_FragCoord.xy, uv = px / uRes;
    vec4 c0 = texture(tCena, uv);
    vec3 col = c0.rgb;
    float k0 = coc(c0.a);
    if (k0 > 0.6) {
      vec3 acc = c0.rgb; float wt = 1.0;
      for (int i = 0; i < 40; i++) {
        float rr = sqrt((float(i) + 0.5) / 40.0) * k0, ang = float(i) * 2.39996;
        vec4 s = texture(tCena, uv + vec2(cos(ang), sin(ang)) * rr / uRes);
        float w = clamp(coc(s.a) - rr + 1.0, 0.0, 1.0);
        acc += s.rgb * w; wt += w;
      }
      col = acc / wt;
    }
    if (uRim > 0.0) {
      float rim = 0.0;
      for (int i = 1; i <= 3; i++) {
        float dl = texture(tCena, uv + uLuz * uRimR * float(i) / 3.0 / uRes).a;
        rim += clamp((c0.a - dl - 0.04) * 5.0, 0.0, 1.0);
      }
      rim = rim / 3.0 * smoothstep(uFocoD - 0.3, uFocoD - 0.06, c0.a);
      float l = dot(col, vec3(0.299, 0.587, 0.114));
      col += uRimCor * rim * uRim * (0.35 + 0.65 * l);
    }
    if (uFl.z > 0.0) {
      // visibilidade da fonte: some atrás do que está perto (média num disco em volta)
      float vis = 0.0;
      for (int i = 0; i < 9; i++) {
        float ang = float(i) * 0.6981;
        vec2 q = (uFl.xy + (i == 0 ? vec2(0.0) : vec2(cos(ang), sin(ang)) * uFl.w * 0.35)) / uRes;
        float d = texture(tCena, clamp(q, vec2(0.0), vec2(1.0))).a;
        vis += 1.0 - smoothstep(uFocoD - 0.25, uFocoD - 0.05, d);
      }
      vis /= 9.0;
      vec2 dl = px - uFl.xy;
      float r2 = dot(dl, dl), s1 = uFl.w;
      float glow = exp(-r2 / (2.0 * s1 * s1)) * 0.55 + exp(-sqrt(r2) / (s1 * 2.2)) * 0.1;
      float risco = exp(-abs(dl.y) / (s1 * 0.05)) * exp(-abs(dl.x) / (uRes.x * 0.35)) * 0.45;
      vec2 cen = uRes * 0.5; float gh = 0.0;
      for (int k = 0; k < 3; k++) {
        float f = k == 0 ? -0.45 : (k == 1 ? -0.85 : 0.4);
        float rg = s1 * (k == 1 ? 1.1 : 0.55);
        vec2 G = cen + (uFl.xy - cen) * f;
        gh += (1.0 - smoothstep(rg * 0.55, rg, length(px - G))) * 0.05;
      }
      col += uFlCor * uFl.z * vis * (glow + risco + gh + 0.02);
    }
    if (uGrao > 0.0) {
      uvec3 g = uvec3(uvec2(px), uint(uQ));
      float n = h(g) + h(g + uvec3(0u, 0u, 7919u)) - 1.0;
      float l = dot(col, vec3(0.299, 0.587, 0.114));
      col += n * uGrao * (0.55 + 0.45 * (1.0 - l));
    }
    o = vec4(clamp(col, 0.0, 1.0), 1.0);
  }`;

  // ------------------------------------------------------------------ matemática 3D
  const mul3 = (A, v) => [A[0] * v[0] + A[1] * v[1] + A[2] * v[2], A[3] * v[0] + A[4] * v[1] + A[5] * v[2], A[6] * v[0] + A[7] * v[1] + A[8] * v[2]];
  const mulT3 = (A, v) => [A[0] * v[0] + A[3] * v[1] + A[6] * v[2], A[1] * v[0] + A[4] * v[1] + A[7] * v[2], A[2] * v[0] + A[5] * v[1] + A[8] * v[2]];
  const mm3 = (A, B) => {
    const r = new Array(9);
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) r[i * 3 + j] = A[i * 3] * B[j] + A[i * 3 + 1] * B[3 + j] + A[i * 3 + 2] * B[6 + j];
    return r;
  };
  const rotY = (a) => { const c = Math.cos(a), s = Math.sin(a); return [c, 0, s, 0, 1, 0, -s, 0, c]; };
  const rotX = (a) => { const c = Math.cos(a), s = Math.sin(a); return [1, 0, 0, 0, c, -s, 0, s, c]; };
  const cor = (hex, pad) => {
    const m = /^#?([0-9a-f]{6})$/i.exec(hex || pad);
    const v = parseInt(m[1], 16);
    return [(v >> 16 & 255) / 255, (v >> 8 & 255) / 255, (v & 255) / 255];
  };

  function carregar(src) {
    return new Promise((ok, falha) => {
      const im = new Image();
      im.onload = () => (im.decode ? im.decode().then(() => ok(im), () => ok(im)) : ok(im));
      im.onerror = () => falha(new Error(`imagem não carregou: ${String(src).slice(0, 80)}`));
      im.src = src;
    });
  }

  function criar(el, op = {}, ctx = {}) {
    const fonte = typeof op.foto === 'string' ? FOTOS[op.foto] : op.foto;
    if (!fonte) throw new Error(`[edin-foto3d] foto "${op.foto}" não registrada: carregue o .foto3d.js gerado pelo edin profundidade antes`);
    const meta = Object.assign({ foco: 0.8, centro: [0.5, 0.45] }, fonte.meta || {});
    const o = Object.assign({ forca: 0.6, foco: 'auto', orbita: 0.12, giro: 0.25, vertigo: 0.35, abertura: 0, rim: false,
      flare: null, vida: true, grao: 0.035, passos: 'auto' }, op);
    const foco = o.foco === 'auto' ? meta.foco : o.foco;
    const rim = o.rim ? Object.assign({ cor: '#ffd9b0', intensidade: 0.5, de: 'direita', largura: 7 }, o.rim === true ? {} : o.rim) : null;
    const flare = o.flare ? Object.assign({ cor: '#ffc68a', intensidade: 0.5, x: 0.5, y: 0.3 }, o.flare) : null;
    const vida = o.vida ? Object.assign({ amp: 0.006, periodo: 4.2, centro: meta.centro, raio: 0.16 }, o.vida === true ? {} : o.vida) : null;
    const inicio = ctx.inicio || 0;
    const avisados = new Set();
    const avisar = (m) => { if (!avisados.has(m)) { avisados.add(m); console.warn(`[edin-foto3d] ${m}`); } };

    const dpr = window.devicePixelRatio || 1;
    const cv = document.createElement('canvas');
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    Object.assign(cv.style, { position: 'absolute', left: '0', top: '0', width: '100%', height: '100%', display: 'block' });
    el.appendChild(cv);
    const gl = cv.getContext('webgl2', { alpha: false, antialias: false, preserveDrawingBuffer: true, premultipliedAlpha: false });
    if (!gl) throw new Error('[edin-foto3d] sem WebGL 2 (no edin html o Chrome headless tem; veja docs/HTML.md)');

    const prog = (fs) => {
      const sh = (tipo, src) => {
        const s = gl.createShader(tipo); gl.shaderSource(s, src); gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error('[edin-foto3d] shader: ' + gl.getShaderInfoLog(s));
        return s;
      };
      const p = gl.createProgram();
      gl.attachShader(p, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs));
      gl.bindAttribLocation(p, 0, 'p'); gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error('[edin-foto3d] link: ' + gl.getProgramInfoLog(p));
      const u = {}; const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
      for (let i = 0; i < n; i++) { const a = gl.getActiveUniform(p, i); u[a.name] = gl.getUniformLocation(p, a.name); }
      return { p, u };
    };
    const pCena = prog(FS_CENA), pPos = prog(FS_POS);
    const vb = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vb);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

    const textura = (img) => {
      const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
      gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, img);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      return t;
    };
    // alvo intermediário (cor + profundidade no alfa) para a pós (desfoque, rim, flare, grão)
    const fbTex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, fbTex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, cv.width, cv.height, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    for (const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.LINEAR], [gl.TEXTURE_MAG_FILTER, gl.LINEAR], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, v);
    const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, fbTex, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);

    let tex = null, pw = 1, ph = 1, su = 1, sv = 1, borda = null;
    const pronto = Promise.all([carregar(fonte.cor), carregar(fonte.fundo || fonte.cor), carregar(fonte.prof)]).then(([ic, ifu, ip]) => {
      pw = ic.naturalWidth; ph = ic.naturalHeight;
      tex = { cor: textura(ic), fundo: textura(ifu), prof: textura(ip) };
      // recorte cover da foto no quadro
      const ar = pw / ph, aq = W / H;
      if (ar > aq) { su = aq / ar; sv = 1; } else { su = 1; sv = ar / aq; }
      // profundidade da borda (para a cobertura): 24 pontos por lado, frente e fundo
      const n = 24, c2 = document.createElement('canvas'); c2.width = 96; c2.height = Math.max(8, Math.round(96 * ph / pw));
      const x2 = c2.getContext('2d'); x2.drawImage(ip, 0, 0, c2.width, c2.height);
      const dd = x2.getImageData(0, 0, c2.width, c2.height).data;
      const amostra = (u, v, ch) => { const i = Math.min(c2.width - 1, Math.round(u * (c2.width - 1))), j = Math.min(c2.height - 1, Math.round(v * (c2.height - 1))); return dd[(j * c2.width + i) * 4 + ch] / 255; };
      const u0 = 0.5 - 0.5 * su, u1 = 0.5 + 0.5 * su, v0 = 0.5 - 0.5 * sv, v1 = 0.5 + 0.5 * sv;
      borda = [];
      for (let i = 0; i <= n; i++) {
        const f = i / n;
        for (const [u, v] of [[lerp(u0, u1, f), v0], [u1, lerp(v0, v1, f)], [lerp(u1, u0, f), v1], [u0, lerp(v1, v0, f)]]) {
          for (const ch of [0, 1]) borda.push([u, v, amostra(u, v, ch)]);
        }
      }
    });
    if (EV.esperar) EV.esperar(pronto);

    const wDe = (d) => 1 + o.forca * (d - foco);
    // ponto da foto (uv, profundidade) no mundo: a câmera neutra vê a foto original
    const mundo = (u, v, d) => {
      const Z = 1 / wDe(d);
      const nx = (u - 0.5) * 2 / su, ny = (0.5 - v) * 2 / sv;
      return [nx * Z / FX, ny * Z / FY, -Z];
    };

    function cameraDe(st) {
      const O = [(st.alvo[0] - 0.5) * 2, (0.5 - st.alvo[1]) * 2];
      const P = [O[0] / FX, O[1] / FY, -1]; // pivô: o alvo na distância do foco (Z = 1)
      let c = [0, 0, 0], m = 1;
      // dolly: anda pelo raio do alvo até o sujeito escalar S
      const S = Math.max(0.2, st.S);
      const dz = 1 - 1 / S;
      // dolly-zoom: anda e compensa a lente; o fundo (d = 0) escala 1 + vertigo
      let dzv = 0;
      const v = (st.vertigo || 0) * o.vertigo;
      if (Math.abs(v) > 1e-5) {
        const b = Math.min(6, 1 / Math.max(0.05, wDe(0))), r = 1 + v;
        const den = r - b;
        if (Math.abs(den) > 1e-4) dzv = (b * (r - 1)) / den;
        m *= (1 - dzv);
      }
      c = [P[0] * (dz + dzv), P[1] * (dz + dzv), -(dz + dzv)];
      // truck/crane: o sujeito anda tx% do quadro
      c[0] += -(st.tx / 100) * 2 / FX;
      c[1] += (st.ty / 100) * 2 / FY;
      // arc/orbit e giros dos presets: a câmera gira em volta do pivô
      // orbita > 0 (arc-left): a câmera vai para a direita em volta do alvo e o fundo anda para a direita
      const fy = ((st.orbita || 0) * o.orbita + (st.ry || 0) * o.giro) * RAD;
      const fx = (-(st.rx || 0) * o.giro) * RAD;
      const Rc = mm3(rotY(fy), rotX(fx));
      const rel = [c[0] - P[0], c[1] - P[1], c[2] - P[2]];
      const rr = mul3(Rc, rel);
      c = [P[0] + rr[0], P[1] + rr[1], P[2] + rr[2]];
      // pós no plano da imagem: lente (zoom), roll, pan/tilt (sem parallax)
      const z = st.zoom || 1, a = (st.rz || 0) * RAD, ca = Math.cos(a), sa = Math.sin(a);
      // rotação em pixels (aspecto certo) escrita em NDC
      const kx = W / 2, ky = H / 2;
      const M = [z * ca, -z * sa * ky / kx, z * sa * kx / ky, z * ca];
      const sh = [(st.px / 100) * 2, -(st.py / 100) * 2];
      return { O, c, Rc, m, M, sh };
    }

    function projetar(cam, X) {
      const r = mulT3(cam.Rc, [X[0] - cam.c[0], X[1] - cam.c[1], X[2] - cam.c[2]]);
      const zc = Math.max(1e-4, -r[2]);
      return [FX * cam.m * r[0] / zc, FY * cam.m * r[1] / zc];
    }

    function cobertura(cam) {
      // menor escala (em volta do alvo) que deixa o quadro inteiro dentro da foto projetada
      const pts = borda.map(([u, v, d]) => {
        const p = projetar(cam, mundo(u, v, d)), q = [p[0] - cam.O[0], p[1] - cam.O[1]];
        return [cam.M[0] * q[0] + cam.M[1] * q[1], cam.M[2] * q[0] + cam.M[3] * q[1]];
      });
      // polígono: a borda em ordem (frente e fundo separados); usa o mais restritivo
      const poligonos = [pts.filter((_, i) => i % 2 === 0), pts.filter((_, i) => i % 2 === 1)];
      const ordena = (pl) => { // quatro lados intercalados -> contorno: reordena por ângulo em volta do centroide
        const cx = pl.reduce((s, p) => s + p[0], 0) / pl.length, cy = pl.reduce((s, p) => s + p[1], 0) / pl.length;
        return pl.slice().sort((a, b) => Math.atan2(a[1] - cy, a[0] - cx) - Math.atan2(b[1] - cy, b[0] - cx));
      };
      const dentro = (pl, x, y) => {
        let ins = false;
        for (let i = 0, j = pl.length - 1; i < pl.length; j = i++) {
          const [xi, yi] = pl[i], [xj, yj] = pl[j];
          if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) ins = !ins;
        }
        return ins;
      };
      const alvos = [];
      for (const fx of [-1, -0.5, 0, 0.5, 1]) for (const fy of [-1, -0.5, 0, 0.5, 1]) if (Math.abs(fx) === 1 || Math.abs(fy) === 1) alvos.push([fx * 1.004, fy * 1.004]);
      let s = 1;
      for (const pl0 of poligonos) {
        const pl = ordena(pl0);
        // pan/tilt rápido (whip) não vira zoom: só até 8% do quadro entra na cobertura, o resto o borrão esconde
        const shx = clamp(cam.sh[0], -0.16, 0.16), shy = clamp(cam.sh[1], -0.16, 0.16);
        const ok = (sc) => alvos.every(([x, y]) => dentro(pl.map(([a, b]) => [cam.O[0] + sc * a + shx, cam.O[1] + sc * b + shy]), x, y));
        if (ok(s)) continue;
        let lo = s, hi = s * 1.05;
        while (!ok(hi) && hi < 4) hi *= 1.15;
        for (let i = 0; i < 18; i++) { const mid = (lo + hi) / 2; if (ok(mid)) hi = mid; else lo = mid; }
        s = hi;
      }
      return s;
    }

    function passosDe(cam, sc) {
      if (o.passos !== 'auto') return [o.passos, Math.max(8, Math.round(o.passos / 3))];
      // tamanho do parallax: quanto o mesmo raio anda na foto entre o perto e o longe, em px do quadro
      let span = 0;
      for (const [x, y] of [[0, 0], [-0.9, -0.9], [0.9, -0.9], [-0.9, 0.9], [0.9, 0.9]]) {
        const a = [cam.Mi[0] * (x - cam.T[0]) + cam.Mi[1] * (y - cam.T[1]) + cam.O[0], cam.Mi[2] * (x - cam.T[0]) + cam.Mi[3] * (y - cam.T[1]) + cam.O[1]];
        const dc = [a[0] / (FX * cam.m), a[1] / (FY * cam.m), -1], rd = mul3(cam.Rc, dc);
        const uvs = [wDe(1), wDe(0)].map((w) => {
          const t = (-1 / w - cam.c[2]) / rd[2];
          const X = [cam.c[0] + rd[0] * t, cam.c[1] + rd[1] * t, cam.c[2] + rd[2] * t];
          return [FX * X[0] / -X[2] * W / 2 * su, FY * X[1] / -X[2] * H / 2 * sv];
        });
        span = Math.max(span, Math.hypot(uvs[0][0] - uvs[1][0], uvs[0][1] - uvs[1][1]) / Math.max(su, sv));
      }
      const n = clamp(Math.ceil(span * dpr / 1.2), 6, 96);
      return [n, Math.max(6, Math.ceil(n / 3))];
    }

    let ultimo = null;
    function desenhar(st, T) {
      if (!tex || !st) return;
      const cam = cameraDe(st);
      const sc = cobertura(cam);
      // pós completo: p = O + sc * M (n - O) + sh  ->  n = Mi (p - O - sh) / sc + O
      const M = cam.M.map((x) => x * sc);
      const det = M[0] * M[3] - M[1] * M[2];
      cam.Mi = [M[3] / det, -M[1] / det, -M[2] / det, M[0] / det];
      cam.T = [cam.O[0] + cam.sh[0], cam.O[1] + cam.sh[1]];
      const PB = [cam.O[0] - (cam.Mi[0] * cam.T[0] + cam.Mi[1] * cam.T[1]), cam.O[1] - (cam.Mi[2] * cam.T[0] + cam.Mi[3] * cam.T[1])];
      const [N, Nb] = passosDe(cam, sc);
      const tg = inicio + (T || 0);
      ultimo = { cobertura: sc, passos: N, camera: cam.c, m: cam.m };
      if (sc > 1.35) avisar(`a câmera pediu ${sc.toFixed(2)}x de cobertura (movimento grande demais para a foto); reduza a intensidade`);

      // ---- passo 1: raio no relevo (frente + fundo)
      gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
      gl.viewport(0, 0, cv.width, cv.height);
      gl.useProgram(pCena.p);
      const u = pCena.u;
      [['tCor', tex.cor], ['tFundo', tex.fundo], ['tProf', tex.prof]].forEach(([nome, t], i) => {
        gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, t); gl.uniform1i(u[nome], i);
      });
      // uRc em coluna (GLSL): transposta da linha
      const R = cam.Rc;
      gl.uniformMatrix3fv(u.uRc, false, [R[0], R[3], R[6], R[1], R[4], R[7], R[2], R[5], R[8]]);
      gl.uniform3fv(u.uC, cam.c);
      gl.uniform2f(u.uF, FX * cam.m, FY * cam.m);
      gl.uniform2f(u.uF0, FX, FY);
      gl.uniformMatrix2fv(u.uPA, false, [cam.Mi[0], cam.Mi[2], cam.Mi[1], cam.Mi[3]]);
      gl.uniform2f(u.uPB, PB[0], PB[1]);
      gl.uniform2f(u.uS, su, sv);
      gl.uniform1f(u.uA, o.forca); gl.uniform1f(u.uDf, foco);
      gl.uniform1i(u.uN, N); gl.uniform1i(u.uNb, Nb);
      gl.uniform1f(u.uAsp, ph / pw);
      if (vida) {
        const a = vida.amp * 0.5 * (1 - Math.cos((2 * Math.PI * tg) / vida.periodo));
        gl.uniform4f(u.uVida, vida.centro[0], vida.centro[1], vida.raio, a);
      } else gl.uniform4f(u.uVida, 0, 0, 1, 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);

      // ---- passo 2: desfoque, rim, flare, grão
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.viewport(0, 0, cv.width, cv.height);
      gl.useProgram(pPos.p);
      const q = pPos.u;
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, fbTex); gl.uniform1i(q.tCena, 0);
      gl.uniform2f(q.uRes, cv.width, cv.height);
      gl.uniform1f(q.uAb, o.abertura * U * dpr); gl.uniform1f(q.uFocoD, foco);
      if (rim) {
        const ang = typeof rim.de === 'number' ? rim.de : { direita: 0, cima: 90, esquerda: 180, baixo: 270 }[rim.de] ?? 0;
        gl.uniform3fv(q.uRimCor, cor(rim.cor, '#ffd9b0')); gl.uniform1f(q.uRim, rim.intensidade);
        gl.uniform1f(q.uRimR, rim.largura * U * dpr); gl.uniform2f(q.uLuz, Math.cos(ang * RAD), Math.sin(ang * RAD));
      } else gl.uniform1f(q.uRim, 0);
      if (flare) {
        // a fonte está no fundo (d = 0): anda com o parallax do fundo
        const p = projetar(cam, mundo(flare.x, flare.y, 0));
        const qq = [p[0] - cam.O[0], p[1] - cam.O[1]];
        const nx = cam.O[0] + sc * (cam.M[0] * qq[0] + cam.M[1] * qq[1]) + cam.sh[0];
        const ny = cam.O[1] + sc * (cam.M[2] * qq[0] + cam.M[3] * qq[1]) + cam.sh[1];
        gl.uniform4f(q.uFl, (nx * 0.5 + 0.5) * cv.width, (ny * 0.5 + 0.5) * cv.height, flare.intensidade, 70 * U * dpr);
        gl.uniform3fv(q.uFlCor, cor(flare.cor, '#ffc68a'));
      } else gl.uniform4f(q.uFl, 0, 0, 0, 1);
      const passo = Math.max(1, Math.floor(FPS / 30 + 1e-9));
      gl.uniform1f(q.uGrao, o.grao); gl.uniform1f(q.uQ, Math.floor(Math.round(EV.quadro(tg) * FPS) / passo) % 997);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    }

    const api = { el, canvas: cv, pronto, meta, desenhar, get ultimo() { return ultimo; }, mundo };
    el.__foto3d = api;
    return api;
  }

  window.EdinFoto3D = { criar, fotos: FOTOS, lente: { fx: FX, fy: FY } };
})();
