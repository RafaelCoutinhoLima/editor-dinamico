/* edin-video.js: núcleo do kit de vídeo em HTML do edin.
 *
 * JavaScript puro, sem build e sem dependências; abre por file://.
 * Contrato com o renderizador (`edin html`): a página recebe ?w=&h=&fps=[&render=1]
 * e define window.EDIN = { duration, seek(t) }. Tudo aqui é função pura do tempo t:
 * nada de CSS animation, setTimeout, requestAnimationFrame (fora da prévia) ou
 * Math.random sem semente. Chamar seek(12), seek(3), seek(7) dá os mesmos quadros
 * que em ordem, o que permite renderizar em paralelo.
 *
 * Uso mínimo:
 *   const v = EdinVideo.video({ fundo: '#0b0820', grao: 0.06, vinheta: 0.4 });
 *   v.cena({ duracao: 3, montar(el, ctx) {...}, atualizar(el, t, p, ctx) {...} });
 *   v.cena({ duracao: 3, entrada: { tipo: 'whip-pan', direcao: 'esquerda' }, ... });
 *   v.iniciar();   // define window.EDIN
 */
(function () {
  'use strict';

  // ------------------------------------------------------------------ parâmetros da URL
  const Q = new URLSearchParams(location.search);
  const num = (k, d) => { const x = parseFloat(Q.get(k)); return Number.isFinite(x) && x > 0 ? x : d; };
  const W = Math.round(num('w', 1080));
  const H = Math.round(num('h', 1920));
  const FPS = num('fps', 30);
  const RENDER = Q.get('render') === '1';
  const CHECAR = !RENDER || Q.get('checar') === '1'; // conferências caras (texto pequeno) só na prévia
  const U = Math.min(W, H) / 1080; // 1 unidade = 1 px num quadro de 1080 de lado menor
  // motion blur do renderizador (`edin html --motion-blur K` passa ?mb=K&obturador=180). Cada seek
  // é um dos K subtempos do obturador; o blur sintético (whip, câmera) cobre só 1/K dele para
  // não somar duas vezes o mesmo rastro.
  const MB = Math.max(1, Math.round(num('mb', 1)));
  const OBT = num('obturador', 180) / 360;
  // início do quadro que contém t. Com --motion-blur o edin chama seek em vários subtempos
  // dentro do mesmo quadro (t + j/K da fração do obturador); tudo que é discreto (dígitos,
  // texto que troca, contagem) usa este tempo para não sair como dois textos sobrepostos.
  const quadro = (t) => Math.floor(t * FPS + 1e-6) / FPS;

  // ------------------------------------------------------------------ matemática
  const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
  const lerp = (a, b, k) => a + (b - a) * k;
  const mix = (a, b, k) => Array.isArray(a) ? a.map((v, i) => lerp(v, b[i], k)) : lerp(a, b, k);

  // cubic-bezier igual ao CSS (Newton + bisseção)
  function bezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = (t) => ((ax * t + bx) * t + cx) * t;
    const sy = (t) => ((ay * t + by) * t + cy) * t;
    const dx = (t) => (3 * ax * t + 2 * bx) * t + cx;
    const resolve = (x) => {
      let t = x;
      for (let i = 0; i < 8; i++) {
        const e = sx(t) - x, d = dx(t);
        if (Math.abs(e) < 1e-6) return t;
        if (Math.abs(d) < 1e-6) break;
        t -= e / d;
      }
      let lo = 0, hi = 1; t = x;
      for (let i = 0; i < 40; i++) { const v = sx(t); if (Math.abs(v - x) < 1e-6) break; if (v < x) lo = t; else hi = t; t = (lo + hi) / 2; }
      return t;
    };
    const f = (p) => (p <= 0 ? 0 : p >= 1 ? 1 : sy(resolve(p)));
    f.css = `cubic-bezier(${x1},${y1},${x2},${y2})`;
    return f;
  }

  // mola determinística (solução analítica do oscilador amortecido).
  // Como easing: p = 1 corresponde a ~assentada (envelope < 0,2%).
  function mola({ amortecimento = 0.7 } = {}) {
    const z = Math.max(0.05, amortecimento);
    const w = z < 1 ? Math.log(500) / z : 9.2;
    const f = (p) => {
      if (p <= 0) return 0; if (p >= 1) return 1;
      const t = p;
      if (z < 1) {
        const wd = w * Math.sqrt(1 - z * z);
        return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z * w / wd) * Math.sin(wd * t));
      }
      return 1 - Math.exp(-w * t) * (1 + w * t);
    };
    return f;
  }

  const ease = {
    linear: (p) => clamp(p),
    smoothstep: (p) => { p = clamp(p); return p * p * (3 - 2 * p); },
    smootherstep: (p) => { p = clamp(p); return p * p * p * (p * (6 * p - 15) + 10); },
    easeInOutCubic: (p) => { p = clamp(p); return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; },
    easeOutCubic: (p) => 1 - Math.pow(1 - clamp(p), 3),
    easeInCubic: (p) => Math.pow(clamp(p), 3),
    expoIn: (p) => { p = clamp(p); return p === 0 ? 0 : Math.pow(2, 10 * p - 10); },
    expoOut: (p) => { p = clamp(p); return p === 1 ? 1 : 1 - Math.pow(2, -10 * p); },
    expoInOut: (p) => { p = clamp(p); if (p === 0 || p === 1) return p; return p < 0.5 ? Math.pow(2, 20 * p - 10) / 2 : (2 - Math.pow(2, -20 * p + 10)) / 2; },
    // nomes do catálogo (higgsfield-camera.md) e da skill de motion
    suave: bezier(0.45, 0, 0.55, 1),
    inOutCubic: bezier(0.65, 0, 0.35, 1),
    inOutQuint: bezier(0.83, 0, 0.17, 1),
    outExpo: bezier(0.16, 1, 0.3, 1),
    inExpo: bezier(0.7, 0, 0.84, 0),
    inCubic: bezier(0.32, 0, 0.67, 0),
    outCubic: bezier(0.33, 1, 0.68, 1),
    out: bezier(0.16, 1, 0.3, 1),
    outSoft: bezier(0.25, 1, 0.5, 1),
    in: bezier(0.7, 0, 0.84, 0),
    inOut: bezier(0.65, 0, 0.35, 1),
    snap: bezier(0.85, 0, 0.15, 1),
    anticipate: bezier(0.36, 0, 0.66, -0.56),
    overshoot: bezier(0.34, 1.56, 0.64, 1),
    mola: mola(),
  };
  const pegaEase = (e, padrao) => (typeof e === 'function' ? e : (e && ease[e]) || padrao || ease.inOutCubic);

  // interp(x, [x0, x1], [y0, y1], easing): sempre com clamp nas pontas
  function interp(x, xs, ys, e) {
    const f = pegaEase(e, ease.linear);
    if (xs.length === 2) return mix(ys[0], ys[1], f((x - xs[0]) / (xs[1] - xs[0] || 1e-9)));
    if (x <= xs[0]) return ys[0];
    for (let i = 1; i < xs.length; i++) if (x <= xs[i]) return mix(ys[i - 1], ys[i], f((x - xs[i - 1]) / (xs[i] - xs[i - 1] || 1e-9)));
    return ys[ys.length - 1];
  }
  // escala em espaço log (crescimento parece uniforme)
  const interpLog = (x, xs, ys, e) => Math.exp(interp(x, xs, ys.map(Math.log), e));

  // quadros-chave: chaves(t, [[0, 1], [0.5, 1.2, 'outExpo'], [2, [10, 20]]])
  // o easing de cada chave vale para o trecho que CHEGA nela (padrão inOutCubic)
  function chaves(t, lista, padrao) {
    if (!lista.length) return 0;
    if (t <= lista[0][0]) return lista[0][1];
    for (let i = 1; i < lista.length; i++) {
      const [t1, v1, e] = lista[i];
      if (t <= t1) { const [t0, v0] = lista[i - 1]; return mix(v0, v1, pegaEase(e, padrao)((t - t0) / (t1 - t0 || 1e-9))); }
    }
    return lista[lista.length - 1][1];
  }

  // ------------------------------------------------------------------ aleatório com semente
  function hash(i, s = 0) {
    let h = (Math.imul(i | 0, 0x27d4eb2d) ^ Math.imul(s | 0, 0x165667b1)) >>> 0;
    h = Math.imul(h ^ (h >>> 15), 0x85ebca6b) >>> 0;
    h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35) >>> 0;
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  }
  // gerador sequencial (mulberry32): use só na montagem, nunca dentro de atualizar
  function aleatorio(semente = 1) {
    let a = (semente * 2654435761) >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  // ruído suave 1D (gradiente, curva quíntica), saída aproximadamente em [-1, 1]
  function ruido(semente = 1) {
    const g = (i) => hash(i, semente) * 2 - 1;
    const n = (x) => {
      const i = Math.floor(x), f = x - i;
      const u = f * f * f * (f * (f * 6 - 15) + 10);
      return 2 * lerp(g(i) * f, g(i + 1) * (f - 1), u);
    };
    const fbm = (x, oitavas = 2) => {
      let s = 0, a = 1, fr = 1, norm = 0;
      for (let o = 0; o < oitavas; o++) { s += a * n(x * fr + o * 17.3); norm += a; a *= 0.5; fr *= 2.03; }
      return s / norm;
    };
    return { n, fbm };
  }

  // ------------------------------------------------------------------ utilidades de DOM
  const px = (n) => `${n * U}px`;
  function estilo(el, obj) { for (const k in obj) { if (k.startsWith('--')) el.style.setProperty(k, obj[k]); else el.style[k] = obj[k]; } return el; }
  function criar(tag, attrs = {}, pai) {
    const el = document.createElement(tag);
    for (const k in attrs) {
      if (k === 'style') estilo(el, attrs.style);
      else if (k === 'html') el.innerHTML = attrs.html;
      else if (k === 'texto') el.textContent = attrs.texto;
      else el.setAttribute(k, attrs[k]);
    }
    if (pai) pai.appendChild(el);
    return el;
  }
  const NS = 'http://www.w3.org/2000/svg';
  function svgDefs(pai) {
    const s = document.createElementNS(NS, 'svg');
    s.setAttribute('width', '0'); s.setAttribute('height', '0');
    s.setAttribute('aria-hidden', 'true');
    s.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;pointer-events:none';
    pai.appendChild(s);
    return s;
  }
  let _idFiltro = 0;
  // filtro de blur direcional (anisotrópico): define(sx, sy) liga/desliga sozinho
  function filtroBlur(defs, el) {
    const id = `edin-blur-${++_idFiltro}`;
    const f = document.createElementNS(NS, 'filter');
    f.setAttribute('id', id);
    f.setAttribute('x', '-10%'); f.setAttribute('y', '-10%'); f.setAttribute('width', '120%'); f.setAttribute('height', '120%');
    f.setAttribute('color-interpolation-filters', 'sRGB');
    const g = document.createElementNS(NS, 'feGaussianBlur');
    g.setAttribute('stdDeviation', '0 0');
    g.setAttribute('edgeMode', 'duplicate');
    f.appendChild(g); defs.appendChild(f);
    return {
      id,
      valor(sx, sy) {
        sx = Math.max(0, sx); sy = Math.max(0, sy);
        if (sx < 0.25 && sy < 0.25) return '';
        g.setAttribute('stdDeviation', `${sx.toFixed(2)} ${sy.toFixed(2)}`);
        return `url(#${id})`;
      },
    };
  }

  // legenda no padrão de Rafael: minúsculas, Sora 700 86 px, sombra suave, fade de 0,2 s.
  // y padrão: 0.68 no vertical (fora dos 450 px da base que a interface do Instagram cobre).
  // Destaque: uma palavra (ou trecho) em laranja, por `destaque: 'nada'` ou `*nada*` no texto.
  // Quebra equilibrada (text-wrap: balance) e sem palavra sozinha na última linha.
  const LARANJA = '#F97316';
  function preencherLegenda(el, texto = '', destaque, corDestaque) {
    el.textContent = '';
    const partes = []; // [texto, destacado]
    if (/\*[^*]+\*/.test(texto)) {
      texto.split(/\*([^*]+)\*/).forEach((s, i) => { if (s) partes.push([s, i % 2 === 1]); });
    } else if (destaque) {
      const lista = (Array.isArray(destaque) ? destaque : [destaque]).filter(Boolean);
      const esc = (x) => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/ +/g, '[ \\u00a0]+');
      const re = new RegExp(`(${lista.map(esc).join('|')})`, 'i');
      texto.split(re).forEach((s, i) => { if (s) partes.push([s, i % 2 === 1]); });
      if (!partes.some((x) => x[1])) console.warn(`[edin] legenda: destaque "${lista.join(', ')}" não aparece em "${texto}"`);
    } else partes.push([texto, false]);
    // sem palavra órfã: o último espaço vira espaço que não quebra (só com 3 palavras ou mais)
    if (texto.trim().split(/\s+/).length >= 3) {
      for (let i = partes.length - 1; i >= 0; i--) {
        const k = (i === partes.length - 1 ? partes[i][0].trimEnd() : partes[i][0]).lastIndexOf(' ');
        if (k >= 0) { partes[i][0] = partes[i][0].slice(0, k) + '\u00a0' + partes[i][0].slice(k + 1); break; }
      }
    }
    for (const [s, d] of partes) {
      if (!d) el.appendChild(document.createTextNode(s));
      else criar('span', { class: 'edin-destaque', texto: s, style: { color: corDestaque } }, el);
    }
  }
  function legenda(pai, { texto, y, tamanho = 86, largura = 0.87, cor = '#fff', destaque = null, corDestaque = LARANJA, classe = '' } = {}) {
    // centro entre 0,55 e 0,75 da altura no vertical (abaixo do sujeito, acima dos 450 px da interface)
    if (y == null) y = H > W ? 0.7 : 0.8;
    const el = criar('div', { class: `edin-legenda ${classe}` }, pai);
    preencherLegenda(el, texto, destaque, corDestaque);
    estilo(el, {
      position: 'absolute', left: '50%', top: `${y * 100}%`, width: `${largura * 100}%`,
      fontSize: px(tamanho), color: cor,
    });
    return {
      el,
      texto(novo, novoDestaque = destaque) { preencherLegenda(el, novo, novoDestaque, corDestaque); },
      // mostra entre [inicio, fim] do relógio que você passar (local ou global).
      // inicio <= 0: já visível no primeiro quadro da cena, sem fade nem subida (capa).
      atualizar(t, inicio, fim, fade = 0.2) {
        const capa = inicio <= 0;
        const a = (capa ? 1 : clamp((t - inicio) / fade)) * clamp((fim - t) / fade);
        const sobe = capa ? 0 : interp(t, [inicio, inicio + 0.33], [14, 0], ease.out);
        el.style.opacity = a.toFixed(4);
        el.style.transform = `translate(-50%, calc(-50% + ${sobe * U}px))`;
      },
    };
  }

  // ------------------------------------------------------------------ luz, halo e poeira
  // Uma luz só no vídeo inteiro (video({ luz: { angulo } })): `angulo` é para onde a sombra cai,
  // em graus a partir do eixo x, sentido horário na tela (60 = para baixo e um pouco à direita,
  // luz vindo de cima à esquerda). sombra(dist, raio, opac) devolve o box-shadow coerente;
  // no CSS use calc(var(--sx) * dist) calc(var(--sy) * dist).
  const LUZ = { angulo: 60, sx: Math.cos(60 * Math.PI / 180), sy: Math.sin(60 * Math.PI / 180) };
  function sombra(dist, raio, opac = 0.5, cor = '8,5,40') {
    return `${(LUZ.sx * dist * U).toFixed(1)}px ${(LUZ.sy * dist * U).toFixed(1)}px ${(raio * U).toFixed(1)}px rgba(${cor},${opac})`;
  }
  // brilho contido: raio no máximo ~10% do lado menor (108 px de design) e opacidade no máximo 0,25.
  // Devolve o trecho de box-shadow/drop-shadow "0 0 Rpx rgba(...)". Pedido acima do teto avisa uma vez.
  const HALO_R = 108, HALO_A = 0.25, _haloAvisos = new Set();
  function halo(raio, opac = 0.2, cor = '249,115,22') {
    if ((raio > HALO_R || opac > HALO_A) && !_haloAvisos.has(`${raio}|${opac}`)) {
      _haloAvisos.add(`${raio}|${opac}`);
      console.warn(`[edin] halo de ${raio} px e opacidade ${opac} limitado a ${HALO_R} px e ${HALO_A} (bloom contido)`);
    }
    return `0 0 ${(Math.min(raio, HALO_R) * U).toFixed(1)}px rgba(${cor},${Math.min(opac, HALO_A)})`;
  }

  // Poeira/partículas em profundidade: cria uma camada data-z dentro da cena (recebe parallax e
  // profundidade de campo da câmera). O movimento é periódico na duração do vídeo: cada partícula dá
  // um número inteiro de voltas, então o último quadro emenda com o primeiro. Use o tempo GLOBAL
  // (ctx.inicio + t) em atualizar, e a mesma semente em cenas vizinhas para a poeira continuar no corte.
  let _durVideo = 0;
  function poeira(pai, { semente = 1, n = 18, z = 0.6, desfoque = 0, tamanho = [3, 7], opacidade = [0.15, 0.45],
    cor = '255,236,214', sobra = 0.1, subida = 1, balanco = 18 } = {}) {
    const camada = criar('div', { 'data-z': String(z), 'data-sobra': String(sobra), 'data-cobre': '0', 'data-decorativo': '' }, pai);
    if (desfoque) camada.setAttribute('data-desfoque', String(desfoque));
    const r = aleatorio(semente), ps = [];
    const LW = W * (1 + 2 * sobra), LH = H * (1 + 2 * sobra);
    for (let i = 0; i < n; i++) {
      const s = lerp(tamanho[0], tamanho[1], r() * r()) * U;
      const el = criar('div', { style: { position: 'absolute', left: '0', top: '0', width: `${s}px`, height: `${s}px`, borderRadius: '50%',
        background: `radial-gradient(circle, rgba(${cor},1) 0%, rgba(${cor},.55) 38%, rgba(${cor},0) 70%)`, willChange: 'transform,opacity' } }, camada);
      ps.push({ el, s, x: r(), y: r(), voltas: subida ? 1 + Math.floor(r() * 2) * subida : 0, fase: r() * 6.283,
        bal: (0.4 + r() * 0.6) * balanco * U, osc: 1 + Math.floor(r() * 3), a: lerp(opacidade[0], opacidade[1], r()) });
    }
    return {
      el: camada,
      atualizar(tg) {
        const P = _durVideo || 30, fase = (2 * Math.PI * tg) / P;
        for (const p of ps) {
          let y = (p.y - (p.voltas * tg) / P) % 1; if (y < 0) y += 1;
          const x = p.x * LW + p.bal * Math.sin(p.osc * fase + p.fase);
          p.el.style.transform = `translate(${(x - p.s / 2).toFixed(1)}px, ${(lerp(-0.05, 1.05, y) * LH - p.s / 2).toFixed(1)}px)`;
          p.el.style.opacity = (p.a * (0.7 + 0.3 * Math.sin(p.osc * 2 * fase + p.fase * 2))).toFixed(3);
        }
      },
    };
  }

  // ------------------------------------------------------------------ CSS base
  const CSS = `
  html,body{margin:0;padding:0;background:#111;overflow:hidden}
  #edin-moldura{position:absolute;left:0;top:0;transform-origin:0 0}
  .edin-palco{position:relative;overflow:hidden;isolation:isolate;contain:strict}
  .edin-palco *,.edin-palco *::before,.edin-palco *::after{transition:none!important}
  .edin-cena{position:absolute;inset:0;transform-origin:0 0}
  .edin-conteudo{position:absolute;inset:0}
  .edin-camada{position:absolute;inset:0}
  .edin-global{position:absolute;inset:0;pointer-events:none;z-index:100000}
  .edin-grao{position:absolute;inset:0;width:100%;height:100%;mix-blend-mode:overlay;image-rendering:auto}
  .edin-cena .edin-legenda,.edin-cena [data-texto]{filter:opacity(var(--edin-portal,1))}
  .edin-legenda{position:absolute;text-align:center;font-family:Sora,system-ui,sans-serif;font-weight:700;line-height:1.12;letter-spacing:-0.02em;
    text-shadow:0 2px 6px rgba(0,0,0,.55),0 6px 34px rgba(0,0,0,.6);text-transform:lowercase;opacity:0;white-space:pre-line;text-wrap:balance;z-index:50}
  #edin-ui{position:fixed;left:0;right:0;bottom:0;height:56px;display:flex;gap:10px;align-items:center;padding:0 14px;
    background:#181826;color:#ddd;font:13px system-ui,sans-serif;z-index:1000000;box-sizing:border-box}
  #edin-ui button{background:#4F46E5;color:#fff;border:0;border-radius:6px;padding:7px 12px;font:600 13px system-ui;cursor:pointer}
  #edin-ui input[type=range]{flex:1}
  #edin-ui .tempo{font-variant-numeric:tabular-nums;min-width:230px}
  html.edin-render #edin-ui{display:none}
  `;

  // ------------------------------------------------------------------ transições
  // Cada transição recebe q (0..1 dentro da janela), as cenas A (sai) e B (entra) e o contexto.
  // Janela: centrada no início de B (b - d/2 a b + d/2), exceto match-cut (b a b + d).
  const DUR_PADRAO = { corte: 0, dissolve: 0.2, 'whip-pan': 0.3, push: 0.5, 'zoom-through': 0.6, 'match-cut': 0.5, fade: 0.4, travessia: 0.9 };
  const SENTIDO = { esquerda: [-1, 0], direita: [1, 0], cima: [0, -1], baixo: [0, 1] };

  function velocidade(f, q, d) { // derivada de f em px/quadro para um percurso de 1 unidade
    const h = 1e-3;
    return ((f(clamp(q + h)) - f(clamp(q - h))) / (Math.min(1, q + h) - Math.max(0, q - h))) / (d * FPS);
  }

  const TRANSICOES = {
    dissolve(q, A, B, tr) {
      B.wrap.style.opacity = pegaEase(tr.easing, ease.smoothstep)(q).toFixed(4);
    },
    fade(q, A, B, tr) { // pelo fundo do vídeo
      const e = pegaEase(tr.easing, ease.smoothstep);
      if (A) A.wrap.style.opacity = (1 - e(clamp(q * 2))).toFixed(4);
      if (B) B.wrap.style.opacity = e(clamp(q * 2 - 1)).toFixed(4);
    },
    'whip-pan'(q, A, B, tr, video, b, t) {
      // com câmera nas duas cenas: o giro é da câmera (CAM_TR abaixo), aqui só o corte no borrão máximo.
      // O quadro que começa exatamente em b (pico do borrão de A) ainda é de A; B entra no quadro seguinte,
      // já perto do pico dele: os dois lados do corte saem igualmente borrados (decidido pelo tempo do
      // quadro, então todos os subtempos do motion blur caem do mesmo lado).
      if (A.cam && B.cam) { (quadro(t) <= b + 1e-6 ? B : A).wrap.style.visibility = 'hidden'; return; }
      // sem câmera (cena sem camadas data-z): tira contínua, A sai e B entra no mesmo sentido
      const [sx, sy] = SENTIDO[tr.direcao || 'esquerda'];
      const e = pegaEase(tr.easing, ease.expoInOut);
      const k = e(q), dist = sx ? W : H;
      const v = Math.abs(velocidade(e, q, tr.duracao)) * dist; // px por quadro
      const comp = Math.min(tr.blurMax || 80 * U, (OBT * v) / MB);
      const bx = sx ? comp / 2 : 0, by = sy ? comp / 2 : 0;
      A.wrap.style.transform = `translate(${sx * k * W}px, ${sy * k * H}px)`;
      B.wrap.style.transform = `translate(${-sx * (1 - k) * W}px, ${-sy * (1 - k) * H}px)`;
      A.wrap.style.filter = A.blur.valor(bx, by);
      B.wrap.style.filter = B.blur.valor(bx, by);
    },
    push(q, A, B, tr) {
      const [sx, sy] = SENTIDO[tr.direcao || 'cima'];
      const e = pegaEase(tr.easing, ease.inOutCubic);
      const k = e(q), dist = sx ? W : H;
      const comp = Math.min(40 * U, (OBT * Math.abs(velocidade(e, q, tr.duracao)) * dist) / MB);
      const bx = sx ? comp / 2 : 0, by = sy ? comp / 2 : 0;
      A.wrap.style.transform = `translate(${sx * k * W}px, ${sy * k * H}px)`;
      B.wrap.style.transform = `translate(${-sx * (1 - k) * W}px, ${-sy * (1 - k) * H}px)`;
      A.wrap.style.filter = A.blur.valor(bx, by);
      B.wrap.style.filter = B.blur.valor(bx, by);
    },
    // travessia: a câmera atravessa o mesmo mundo de A até B (CAM_TR abaixo). Aqui: A fica por cima e
    // o fundo de A some no meio do movimento, revelando o fundo de B; sujeitos e frente nunca somem.
    travessia(q, A, B) {
      A.wrap.style.zIndex = String(parseInt(B.wrap.style.zIndex, 10) + 1);
    },
    // A entra no objeto (alvo, em fração do quadro) e B nasce de dentro dele.
    // Com `raio` (px de design), B aparece primeiro pelo "portal" do objeto, que cresce com o zoom.
    'zoom-through'(q, A, B, tr) {
      const [ax, ay] = tr.alvo || [0.5, 0.5];
      const ox = ax * W, oy = ay * H;
      const SA = tr.escala || 2.5;
      const meio = tr.raio ? 0.45 : 0.5;
      // cúbica e não expo: com expo o disco do portal toma a tela em 2 quadros e vira clarão (+42 de brilho num quadro)
      const eIn = ease.inCubic, eOut = ease.outCubic;
      const qa = clamp(q / meio);
      const sA = Math.exp(Math.log(SA) * eIn(qa));
      const vA = Math.abs(velocidade((x) => Math.exp(Math.log(SA) * eIn(x)), qa, tr.duracao * meio)) * Math.hypot(W, H) / 2;
      A.wrap.style.transformOrigin = `${ox}px ${oy}px`;
      A.wrap.style.transform = `scale(${sA})`;
      A.wrap.style.filter = A.blur.valor(Math.min(20 * U, 0.12 * vA / MB) / sA, Math.min(20 * U, 0.12 * vA / MB) / sA);
      // textos de A somem no começo do mergulho (nada de palavra gigante cortada pelo quadro)
      A.wrap.style.setProperty('--edin-portal', (1 - ease.smoothstep(q / (meio * 0.5))).toFixed(4));
      const qb = clamp((q - meio) / (1 - meio));
      const sB = lerp(tr.escalaB || 1.3, 1, eOut(qb));
      B.wrap.style.transformOrigin = `${ox}px ${oy}px`;
      B.wrap.style.transform = `scale(${sB})`;
      if (tr.raio) {
        const rPortal = tr.raio * U * sA;
        const cobre = Math.hypot(Math.max(ox, W - ox), Math.max(oy, H - oy)) / sB + 2;
        const r = q < meio ? rPortal : lerp(tr.raio * U * SA, cobre, eOut(qb));
        if (q < meio * 0.35) B.wrap.style.visibility = 'hidden';
        else B.wrap.style.clipPath = `circle(${r.toFixed(1)}px at ${ox}px ${oy}px)`;
        // B dissolve dentro do portal (o objeto de A vira a cena B, sem troca seca de cor)
        if (q < meio) B.wrap.style.opacity = ease.smoothstep((q - meio * 0.35) / (meio * 0.6)).toFixed(4);
        if (q >= meio && qb > 0.999) B.wrap.style.clipPath = '';
        // textos de B só aparecem quando o portal já passou de ~60% do quadro (nada de palavra cortada no círculo)
        const fr = r / cobre;
        B.wrap.style.setProperty('--edin-portal', ease.smoothstep((fr - 0.6) / 0.3).toFixed(4));
      } else if (q < meio) B.wrap.style.visibility = 'hidden';
      else { A.wrap.style.visibility = 'hidden'; B.wrap.style.setProperty('--edin-portal', ease.smoothstep(qb / 0.5).toFixed(4)); }
    },
    // elemento [data-match=nome] continua no mesmo lugar: B começa encaixado no elemento de A
    // (congelado no instante do corte) e assenta no próprio enquadramento em `duracao`.
    'match-cut'(q, A, B, tr, video, b) {
      A.wrap.style.display = ''; // presente no layout só para medir
      A.wrap.style.visibility = 'hidden';
      const nome = tr.elemento;
      if (!nome) return;
      const ea = A.el.querySelector(`[data-match="${nome}"]`);
      const eb = B.el.querySelector(`[data-match="${nome}"]`);
      if (!ea || !eb) { video.avisar(`match-cut: [data-match="${nome}"] não existe nas duas cenas`); return; }
      // A congelado no corte, só para medir
      video._atualizarCena(A, b);
      const ra = video.retangulo(ea), rb0 = video.retangulo(eb);
      // escalaMax: limita a escala inicial de B (página clara que encheria o quadro vira clarão);
      // o centro continua encaixado no elemento de A
      const ka = Math.min(tr.escalaMax || Infinity, Math.sqrt((ra.width * ra.height) / Math.max(1, rb0.width * rb0.height)));
      const cA = [ra.left + ra.width / 2, ra.top + ra.height / 2];
      const cB = [rb0.left + rb0.width / 2, rb0.top + rb0.height / 2];
      if (!tr._conferido && !tr.escalaMax) {
        tr._conferido = true;
        const dc = Math.hypot(cA[0] - cB[0], cA[1] - cB[1]) / Math.hypot(W, H);
        if (tr.duracao === 0 && (dc > 0.02 || Math.abs(ka - 1) > 0.1))
          video.avisar(`match-cut "${nome}": centro difere ${(dc * 100).toFixed(1)}% e escala ${ka.toFixed(2)}x; use duracao > 0 para encaixar ou alinhe as cenas`);
      }
      if (tr.duracao === 0) return;
      const e = pegaEase(tr.easing, ease.outCubic)(q);
      const k = lerp(ka, 1, e);
      // x' = k x + (cA - k cB) interpolado até identidade
      const tx = lerp(cA[0] - ka * cB[0], 0, e), ty = lerp(cA[1] - ka * cB[1], 0, e);
      B.wrap.style.transformOrigin = '0 0';
      B.wrap.style.transform = `translate(${tx}px, ${ty}px) scale(${k})`;
      if (tr.dissolve) {
        const qd = (q * tr.duracao) / tr.dissolve;
        if (qd < 1) { A.wrap.style.visibility = ''; B.wrap.style.opacity = ease.smoothstep(qd).toFixed(4); }
      }
    },
  };

  // Transições que são movimento de câmera: devolvem, para A e B, um estado parcial de câmera em função
  // do progresso q (0..1 na janela). O kit soma isso à câmera da cena (o blur de movimento e a escala de
  // cobertura saem da própria câmera, sem borda de camada). Fora de [0, 1] o percurso continua em linha
  // reta, para a velocidade no instante do corte ser medida certa.
  const inExpoX = (u) => (u <= 1 ? ease.inExpo(u) : 1 + 6.25 * (u - 1));      // 6,25 = inclinação final de inExpo
  const outExpoX = (u) => (u >= 0 ? ease.outExpo(u) : 6.25 * u);             // e inicial de outExpo: velocidades iguais no corte
  const CAM_TR = {
    // whip pan de verdade: A gira até o borrão máximo, corte seco no meio, B sai do borrão no mesmo sentido.
    // `percurso` (% do quadro, padrão 35) de cada lado; o fundo precisa de data-sobra (a cobertura escala o resto).
    'whip-pan'(q, tr, lado) {
      const [sx, sy] = SENTIDO[tr.direcao || 'esquerda'], P = tr.percurso || 35;
      const k = lado === 'A' ? inExpoX(q / 0.5) : -(1 - outExpoX((q - 0.5) / 0.5));
      return { px: sx * P * k, py: sy * P * k, blurMax: tr.blurMax || 110 * U, ids: ['whip-pan'] };
    },
    // travessia: a câmera anda de A até B pelo mesmo espaço (com parallax: fundo anda menos que a frente).
    // `distancia` em quadros (padrão 1); o fundo de A some entre 15% e 55% do percurso.
    travessia(q, tr, lado) {
      const [sx, sy] = SENTIDO[tr.direcao || 'cima'], Dd = 100 * (tr.distancia || 1);
      const e = pegaEase(tr.easing, ease.inOutCubic)(q);
      const k = lado === 'A' ? e : -(1 - e);
      const st = { tx: sx * Dd * k, ty: sy * Dd * k, blurMax: tr.blurMax || 80 * U, ids: ['travessia'] };
      if (lado === 'A') st.opFundo = 1 - ease.smoothstep((q - 0.15) / 0.4);
      return st;
    },
  };

  // ------------------------------------------------------------------ grão e vinheta globais
  // grão de película: um padrão novo a cada `passo` quadros (passo = piso(fps / graoHz)): 30 fps troca todo
  // quadro, 60 fps troca a cada 2 (30 Hz, como película projetada). Determinístico pelo número do quadro.
  function criarGrao(pai, intensidade, graoHz) {
    const c = criar('canvas', { class: 'edin-grao' }, pai);
    c.width = Math.ceil(W / 2); c.height = Math.ceil(H / 2);
    c.style.opacity = String(intensidade);
    const ctx = c.getContext('2d');
    const TILE = 256, N = 8, pads = [];
    for (let k = 0; k < N; k++) {
      const t = document.createElement('canvas'); t.width = t.height = TILE;
      const tc = t.getContext('2d'), img = tc.createImageData(TILE, TILE), r = aleatorio(1000 + k);
      for (let i = 0; i < TILE * TILE; i++) {
        const v = Math.round(128 + ((r() + r() + r()) / 3 - 0.5) * 2 * 160);
        img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = clamp(v, 0, 255); img.data[i * 4 + 3] = 255;
      }
      tc.putImageData(img, 0, 0);
      pads.push(ctx.createPattern(t, 'repeat'));
    }
    const passo = Math.max(1, Math.floor(FPS / (graoHz || 30) + 1e-9));
    return (nq) => {
      const quadro = Math.floor(nq / passo);
      const k = Math.floor(hash(quadro, 7) * N), dx = Math.floor(hash(quadro, 11) * TILE), dy = Math.floor(hash(quadro, 13) * TILE);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.translate(-dx, -dy);
      ctx.fillStyle = pads[k];
      ctx.fillRect(dx, dy, c.width, c.height);
    };
  }

  // ------------------------------------------------------------------ vídeo
  function video(opcoes = {}) {
    const op = Object.assign({ fundo: '#0b0820', grao: 0.06, graoHz: 30, vinheta: 0.4, tom: null, grade: null, luz: null }, opcoes);
    if (op.luz && op.luz.angulo != null) {
      LUZ.angulo = op.luz.angulo; LUZ.sx = Math.cos(LUZ.angulo * Math.PI / 180); LUZ.sy = Math.sin(LUZ.angulo * Math.PI / 180);
    }
    const cenas = [], camadas = [], avisados = new Set();
    let palco, defs, globalEl, grao, pronto = null, duracao = 0, montado = false;

    const v = {
      w: W, h: H, fps: FPS, u: U, render: RENDER, mb: MB,
      get duracao() { return duracao; },
      avisar(msg) { if (!avisados.has(msg)) { avisados.add(msg); console.warn(`[edin] ${msg}`); } },
      cena(cfg) { cenas.push({ cfg }); return v; },
      // camada global por cima das cenas (legenda que atravessa cenas, logo, tom de cor)
      camada(cfg) { camadas.push({ cfg }); return v; },
      retangulo(el) { // retângulo em px do quadro, independente da escala da prévia
        const rp = palco.getBoundingClientRect(), r = el.getBoundingClientRect(), s = rp.width / W;
        return { left: (r.left - rp.left) / s, top: (r.top - rp.top) / s, width: r.width / s, height: r.height / s };
      },
      iniciar() {
        montar(); definirEDIN();
        if (!RENDER) previa();
        // ?t=5.2 desenha esse instante ao abrir (útil para print com --screenshot)
        else pronto.then(() => desenhar(num('t', 0) || 0));
        return v;
      },
      desenhar: (t) => desenhar(t),
      get palco() { return palco; },
      get cenas() { return cenas; },
    };

    function normalizaTr(tr, padraoDir) {
      if (!tr) return null;
      if (typeof tr === 'string') tr = { tipo: tr };
      tr = Object.assign({}, tr);
      if (!TRANSICOES[tr.tipo] && tr.tipo !== 'corte') { v.avisar(`transição desconhecida "${tr.tipo}", usando corte`); tr.tipo = 'corte'; }
      if (tr.duracao == null) tr.duracao = DUR_PADRAO[tr.tipo] ?? 0;
      if (tr.tipo === 'corte') tr.duracao = 0;
      if (!tr.direcao && padraoDir) tr.direcao = padraoDir;
      return tr;
    }

    function montar() {
      if (montado) return; montado = true;
      const st = document.createElement('style'); st.textContent = CSS; document.head.prepend(st);
      if (RENDER) document.documentElement.classList.add('edin-render');
      palco = (op.raiz && document.querySelector(op.raiz)) || document.getElementById('palco');
      if (!palco) { palco = criar('div', { id: 'palco' }); document.body.appendChild(palco); }
      const moldura = criar('div', { id: 'edin-moldura' });
      palco.parentNode.insertBefore(moldura, palco); moldura.appendChild(palco);
      palco.classList.add('edin-palco');
      estilo(palco, { width: `${W}px`, height: `${H}px`, background: op.fundo, '--w': `${W}px`, '--h': `${H}px`, '--u': `${U}px`,
        '--sx': `${(LUZ.sx * U).toFixed(4)}px`, '--sy': `${(LUZ.sy * U).toFixed(4)}px` });
      palco.classList.add(W >= H ? 'horizontal' : 'vertical');
      defs = svgDefs(palco);

      // linha do tempo: inicio padrão = fim da cena anterior
      let fim = 0;
      cenas.forEach((c, i) => {
        const cfg = c.cfg;
        c.i = i; c.id = cfg.id || `cena${i + 1}`;
        c.inicio = cfg.inicio != null ? cfg.inicio : fim;
        c.duracao = cfg.duracao != null ? cfg.duracao : 3;
        c.fim = c.inicio + c.duracao; fim = c.fim;
        c.wrap = criar('div', { class: 'edin-cena', 'data-cena': c.id }, palco);
        c.wrap.style.zIndex = String(10 + i);
        c.el = criar('div', { class: 'edin-conteudo' }, c.wrap);
        if (cfg.classe) c.el.className += ' ' + cfg.classe;
        if (cfg.html) c.el.innerHTML = cfg.html;
        c.blur = filtroBlur(defs, c.wrap);
        c.ctx = { w: W, h: H, u: U, fps: FPS, id: c.id, inicio: c.inicio, duracao: c.duracao, video: v, defs, vertical: H > W };
      });
      duracao = op.duracao || fim;
      _durVideo = duracao;
      // transições: entrada de B vale para a fronteira A|B; senão a saida de A
      cenas.forEach((c, i) => {
        const ant = cenas[i - 1];
        c.trEntrada = normalizaTr(c.cfg.entrada || (ant && ant.cfg.saida) || null);
        if (c.trEntrada && c.trEntrada.tipo === 'match-cut' && !c.trEntrada.elemento) c.trEntrada.elemento = 'match';
        if (ant && Math.abs(ant.fim - c.inicio) > 1e-6) v.avisar(`${c.id} começa em ${c.inicio}s mas ${ant.id} acaba em ${ant.fim}s; a fronteira usada é o início de ${c.id}`);
      });
      const ult = cenas[cenas.length - 1];
      if (ult) ult.trSaidaFinal = ult.cfg.saida ? normalizaTr(ult.cfg.saida) : null;

      cenas.forEach((c) => { if (c.cfg.montar) c.cfg.montar(c.el, c.ctx); });
      // toda cena com camadas ganha câmera (mesmo sem `camera`): as transições de câmera precisam dela
      cenas.forEach((c) => { if (window.EdinCam && (c.cfg.camera || c.el.querySelector('[data-z],[data-tela]'))) c.cam = window.EdinCam.camera(c.el, c.ctx); });

      globalEl = criar('div', { class: 'edin-global' }, palco);
      camadas.forEach((g, i) => {
        g.el = criar('div', { class: 'edin-camada' }, globalEl);
        g.el.style.zIndex = String(i + 1);
        g.ctx = { w: W, h: H, u: U, fps: FPS, video: v };
        if (g.cfg.montar) g.cfg.montar(g.el, g.ctx);
        // camada global que começa/acaba no meio de uma cena sem fade = salto visível
        const fronteiras = [0, duracao, ...cenas.map((c) => c.inicio)];
        for (const lim of [g.cfg.inicio, g.cfg.fim]) {
          if (lim == null || (g.cfg.fade || 0) >= 0.1) continue;
          if (!fronteiras.some((f) => Math.abs(f - lim) < 0.05)) v.avisar(`camada global corta seco em ${lim}s no meio de uma cena; use fade >= 0.1 ou alinhe com uma transição`);
        }
      });
      if (op.tom) criar('div', { class: 'edin-camada', style: { background: op.tom.cor, mixBlendMode: op.tom.modo || 'soft-light', opacity: String(op.tom.opacidade ?? 0.3) } }, globalEl);
      // grade de cor única: luzes quentes do lado da luz, sombras frias do outro (soft-light, constante)
      if (op.grade) {
        const g = op.grade, a = LUZ.angulo + 90; // gradiente na direção da luz: começa no lado de onde ela vem
        criar('div', { class: 'edin-camada', style: { background: `linear-gradient(${a}deg, ${g.luzes || '#ffb27a'} 0%, rgba(128,128,128,0) 55%, ${g.sombras || '#1f2a6b'} 100%)`,
          mixBlendMode: 'soft-light', opacity: String(g.forca ?? 0.35) } }, globalEl);
      }
      if (op.vinheta) criar('div', { class: 'edin-camada', style: { background: `radial-gradient(ellipse 78% 64% at 50% 48%, rgba(0,0,0,0) 55%, rgba(0,0,0,${op.vinheta}) 100%)` } }, globalEl);
      if (op.grao) grao = criarGrao(globalEl, op.grao, op.graoHz);

      // segurança de determinismo: Math.random vira semeado (e avisa)
      const r = aleatorio(12345);
      Math.random = function () { v.avisar('Math.random() chamado: trocado por gerador com semente; use EdinVideo.aleatorio(semente) na montagem'); return r(); };

      pronto = esperarRecursos();
    }

    async function esperarRecursos() {
      try {
        const fs = [];
        document.fonts.forEach((f) => fs.push(f.load().catch(() => v.avisar(`fonte não carregou: ${f.family} ${f.weight}`))));
        await Promise.all(fs);
        await document.fonts.ready;
      } catch (e) { /* sem FontFaceSet */ }
      const imgs = [...palco.querySelectorAll('img')];
      await Promise.all(imgs.map((im) => (im.decode ? im.decode() : Promise.resolve()).catch(() => v.avisar(`imagem não carregou: ${im.getAttribute('src')}`))));
      if (op.precarregar) await precarregar(op.precarregar);
      // animações CSS que existirem ficam presas ao relógio do vídeo
      v._animacoesCSS = document.getAnimations ? document.getAnimations() : [];
      if (v._animacoesCSS.length) v.avisar(`${v._animacoesCSS.length} animação(ões) CSS encontradas; elas serão pausadas e sincronizadas com t, mas prefira atualizar()`);
    }

    // estado de uma fronteira entre cenas
    function janela(B) {
      const tr = B.trEntrada;
      if (!tr) return null;
      const b = B.inicio;
      // match-cut seco: um quadro de janela só para conferir o alinhamento
      if (tr.tipo === 'match-cut' && tr.duracao === 0 && B.i > 0) return { a: b, z: b + 1 / FPS, tr };
      if (tr.duracao === 0) return null;
      if (B.i === 0) return { a: b, z: b + tr.duracao, tr };
      if (tr.tipo === 'match-cut') return { a: b, z: b + tr.duracao, tr };
      return { a: b - tr.duracao / 2, z: b + tr.duracao / 2, tr };
    }

    v._atualizarCena = function (c, t) {
      const tl = t - c.inicio;
      c.ctx.tq = quadro(t);            // tempo global do quadro (para valores discretos)
      c.ctx.tql = c.ctx.tq - c.inicio; // o mesmo, no relógio local da cena
      c.ctx.tg = t;                    // tempo global contínuo (poeira, coisas que atravessam cenas)
      const p = clamp(tl / c.duracao);
      if (c.cfg.atualizar) c.cfg.atualizar(c.el, tl, p, c.ctx);
      if (c.cam) {
        const EC = window.EdinCam, mov = c.cfg.camera, ex = c.extra;
        let m = mov;
        if (ex) m = (pp, tt, D) => EC.combinar([typeof mov === 'function' ? mov(pp, tt, D) : Object.assign(EC.neutro(), mov || {}),
          Object.assign(EC.neutro(), ex(tt + c.inicio))]);
        c.cam.aplicar(m, p, tl);
      }
    };

    function desenhar(tIn) {
      const t = clamp(tIn, 0, Math.max(0, duracao - 1e-6));
      const nq = Math.round(quadro(t) * FPS); // mesmo número em todos os subtempos do quadro
      // 1) quem aparece
      cenas.forEach((c, i) => {
        const prox = cenas[i + 1];
        const jE = janela(c), jS = prox ? janela(prox) : null;
        let a = c.inicio, z = c.fim;
        if (jE && i > 0) a = Math.min(a, jE.a);
        if (prox) z = jS ? (jS.tr.tipo === 'match-cut' ? prox.inicio : jS.z) : prox.inicio;
        c.visivel = t >= a && (t < z || (i === cenas.length - 1 && t <= z));
        const w = c.wrap;
        w.style.display = c.visivel ? '' : 'none';
        w.style.opacity = ''; w.style.transform = ''; w.style.filter = ''; w.style.clipPath = '';
        w.style.visibility = ''; w.style.transformOrigin = '';
        w.style.zIndex = String(10 + i); w.style.removeProperty('--edin-portal');
        c.extra = null;
      });
      // 1b) transições que são câmera: A e B recebem o movimento antes de desenhar
      cenas.forEach((B, i) => {
        const j = janela(B);
        if (!j || i === 0 || !CAM_TR[j.tr.tipo] || t < j.a || t >= j.z) return;
        const A = cenas[i - 1];
        if (!A.cam || !B.cam) return;
        const f = CAM_TR[j.tr.tipo], qd = (tg) => (tg - j.a) / (j.z - j.a);
        A.extra = (tg) => f(qd(tg), j.tr, 'A');
        B.extra = (tg) => f(qd(tg), j.tr, 'B');
      });
      // 2) conteúdo
      cenas.forEach((c) => { if (c.visivel) v._atualizarCena(c, t); });
      // 3) transições ativas
        let emTransicao = false;
      cenas.forEach((B, i) => {
        const j = janela(B);
        if (!j || t < j.a || t >= j.z) return;
        emTransicao = true;
        const q = clamp((t - j.a) / (j.z - j.a));
        if (i === 0) { B.wrap.style.opacity = ease.smoothstep(q).toFixed(4); return; }
        const A = cenas[i - 1];
        TRANSICOES[j.tr.tipo](q, A, B, j.tr, v, B.inicio, t);
      });
      const ult = cenas[cenas.length - 1];
      if (ult && ult.trSaidaFinal && ult.trSaidaFinal.duracao > 0) {
        const q = clamp((t - (ult.fim - ult.trSaidaFinal.duracao)) / ult.trSaidaFinal.duracao);
        if (q > 0) ult.wrap.style.opacity = (1 - ease.smoothstep(q)).toFixed(4);
      }
      // 4) camadas globais
      camadas.forEach((g) => {
        const c = g.cfg, ini = c.inicio ?? 0, fi = c.fim ?? duracao, fd = c.fade || 0;
        const vis = t >= ini && t <= fi;
        g.el.style.display = vis ? '' : 'none';
        if (!vis) return;
        g.el.style.opacity = fd > 0 ? String(clamp((t - ini) / fd) * clamp((fi - t) / fd)) : '';
        g.ctx.tq = quadro(t);
        if (c.atualizar) c.atualizar(g.el, t, clamp((t - ini) / ((fi - ini) || 1)), g.ctx);
      });
      if (grao) grao(nq);
      if (v._animacoesCSS) v._animacoesCSS.forEach((a) => { try { a.pause(); a.currentTime = t * 1000; } catch (e) { /* */ } });
      v.t = t;
      if (CHECAR && !emTransicao) checarTexto(t);
      if (v._aoDesenhar) v._aoDesenhar(t);
    }

    // prévia (ou ?checar=1): avisa texto visível com altura de maiúscula abaixo de 45 px no quadro de 1080
    // (Sora: maiúscula = 0,7 da fonte, então fonte mínima ~64 px). Conta a escala da câmera e de transform.
    // Ignora [data-decorativo] (interrogações de fundo, números de enfeite). Fora das transições.
    const MAIUSCULA_MIN = op.maiusculaMin || 45, CAP = op.capRatio || 0.7, pequenos = new Set();
    function checarTexto(t) {
      const rp = palco.getBoundingClientRect(), s = rp.width / W;
      if (!s) return;
      cenas.forEach((c) => {
        if (!c.visivel) return;
        const tw = document.createTreeWalker(c.el, NodeFilter.SHOW_TEXT);
        const vistos = new Set();
        for (let n = tw.nextNode(); n; n = tw.nextNode()) {
          const txt = n.nodeValue.trim();
          const el = n.parentElement;
          if (!txt || !el || vistos.has(el) || el.closest('svg') || el.closest('[data-decorativo]')) continue;
          vistos.add(el);
          if (!el.offsetHeight) continue;
          const cs = getComputedStyle(el);
          if (cs.visibility === 'hidden') continue;
          let a = 1;
          for (let e = el; e && e !== palco && a >= 0.05; e = e.parentElement) a *= parseFloat(getComputedStyle(e).opacity);
          if (a < 0.05) continue;
          const r = el.getBoundingClientRect();
          if (r.right <= rp.left || r.left >= rp.right || r.bottom <= rp.top || r.top >= rp.bottom) continue;
          const fonte = (parseFloat(cs.fontSize) * (r.height / el.offsetHeight)) / s / U;
          const chave = `${c.id}|${txt}`;
          if (fonte * CAP < MAIUSCULA_MIN - 0.5 && !pequenos.has(chave)) {
            pequenos.add(chave);
            v.avisar(`texto pequeno na cena ${c.id} (t=${t.toFixed(2)}s): "${txt.slice(0, 32)}" com maiúscula de ${(fonte * CAP).toFixed(0)} px (fonte ${fonte.toFixed(0)} px) no quadro de 1080; mínimo ${MAIUSCULA_MIN} px de maiúscula`);
          }
        }
      });
    }

    function definirEDIN() {
      window.EDIN = {
        duration: duracao,
        fps: FPS, width: W, height: H,
        seek: (t) => pronto.then(() => { desenhar(t); }),
        ready: () => pronto,
      };
    }

    // ---------------------------------------------------------------- prévia no navegador
    function previa() {
      const ui = criar('div', { id: 'edin-ui' }, document.body);
      const bt = criar('button', { texto: 'play' }, ui);
      const rg = criar('input', { type: 'range', min: '0', max: String(duracao), step: String(1 / FPS), value: '0' }, ui);
      const lb = criar('span', { class: 'tempo' }, ui);
      const moldura = document.getElementById('edin-moldura');
      const ajusta = () => {
        const s = Math.min(window.innerWidth / W, (window.innerHeight - 56) / H);
        moldura.style.transform = `translate(${(window.innerWidth - W * s) / 2}px, 0) scale(${s})`;
      };
      ajusta(); window.addEventListener('resize', ajusta);
      let tocando = false, t0 = 0, tIni = 0, tAtual = 0;
      const fmt = (t) => `${String(Math.floor(t / 60)).padStart(2, '0')}:${(t % 60).toFixed(2).padStart(5, '0')}`;
      const ir = (t) => {
        tAtual = clamp(t, 0, duracao);
        desenhar(tAtual);
        rg.value = String(tAtual);
        const c = cenas.find((x) => tAtual >= x.inicio && tAtual < x.fim) || cenas[cenas.length - 1];
        lb.textContent = `${fmt(tAtual)} / ${fmt(duracao)}  ·  quadro ${Math.round(tAtual * FPS)}  ·  ${c ? c.id : ''}`;
      };
      const loop = (agora) => {
        if (!tocando) return;
        const t = tIni + (agora - t0) / 1000;
        if (t >= duracao) { ir(duracao); tocando = false; bt.textContent = 'play'; return; }
        ir(t); requestAnimationFrame(loop);
      };
      const tocar = () => {
        if (tocando) { tocando = false; bt.textContent = 'play'; return; }
        if (tAtual >= duracao - 1e-3) tAtual = 0;
        tocando = true; bt.textContent = 'pausa'; t0 = performance.now(); tIni = tAtual; requestAnimationFrame(loop);
      };
      bt.onclick = tocar;
      rg.oninput = () => { tocando = false; bt.textContent = 'play'; ir(parseFloat(rg.value)); };
      window.addEventListener('keydown', (e) => {
        if (e.code === 'Space') { e.preventDefault(); tocar(); }
        if (e.code === 'ArrowRight') ir(tAtual + (e.shiftKey ? 1 : 1 / FPS));
        if (e.code === 'ArrowLeft') ir(tAtual - (e.shiftKey ? 1 : 1 / FPS));
      });
      pronto.then(() => ir(num('t', 0) || 0));
    }

    return v;
  }

  async function precarregar(urls) {
    await Promise.all(urls.map((u) => new Promise((ok) => {
      const im = new Image(); im.onload = () => (im.decode ? im.decode().then(ok, ok) : ok()); im.onerror = () => { console.warn(`[edin] imagem não carregou: ${u}`); ok(); }; im.src = u;
    })));
  }

  window.EdinVideo = {
    w: W, h: H, fps: FPS, u: U, render: RENDER, vertical: H > W, mb: MB, obturador: OBT,
    luz: LUZ, sombra, halo, poeira,
    video, quadro, ease, bezier, mola, interp, interpLog, chaves, clamp, lerp, mix,
    ruido, aleatorio, hash, px, estilo, criar, legenda, precarregar, svgDefs, filtroBlur,
    transicoes: TRANSICOES,
  };
})();
