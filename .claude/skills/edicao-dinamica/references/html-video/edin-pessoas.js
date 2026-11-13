/* edin-pessoas.js: pessoas estilizadas em código para o kit de vídeo em HTML do edin.
 *
 * JavaScript puro, sem dependências, abre por file://. Funciona sozinho ou junto com edin-video.js e
 * edin-cam.js (multidão em camadas data-z para o parallax da câmera). Tudo é função pura de t: seek fora
 * de ordem dá o mesmo quadro.
 *
 * - Rig 2D por esqueleto (cabeça, pescoço, tronco em 2 segmentos, ombros, cotovelos, mãos com dedos,
 *   quadril, joelhos, pés), cinemática direta por ângulos de junta + IK de 2 ossos opcional para as mãos.
 *   Proporção de 7,5 cabeças. Unidade interna: 1 cabeça = 100 unidades de desenho.
 * - Três estilos com a mesma pose: 'silhueta' (contraluz com luz de recorte), 'ilustracao' (cores chapadas),
 *   'traco' (linha de caneta de espessura variável).
 * - Poses, mistura, ciclos (andar, correr, comemorar), respiração/balanço/piscar sempre ativos, olhar para
 *   um alvo, multidão em profundidade e closes de detalhe.
 *
 * Convenções de ângulo (graus): membro com 0 = pendurado para baixo, positivo = gira para a frente (para
 * onde a pessoa olha, +x antes do espelho). Cotovelo e joelho positivos = dobrar no sentido natural.
 * tronco/peito/pescoco/cabeca positivos = inclinar para a frente (cabeça baixa); negativos = olhar para cima.
 * 'giro' 0 = perfil (olhando para a direita), 1 = de frente para a câmera; 'dir: -1' espelha (olha para a
 * esquerda). Braço/perna 'P' = do lado de perto da câmera, 'L' = do lado de longe.
 */
(function () {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const RAD = Math.PI / 180;
  const TAU = Math.PI * 2;
  const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
  const lerp = (a, b, k) => a + (b - a) * k;
  const suave = (p) => { p = clamp(p); return p * p * p * (p * (p * 6 - 15) + 10); };
  const EASE = {
    linear: (p) => clamp(p),
    suave,
    inOut: (p) => { p = clamp(p); return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; },
    out: (p) => 1 - Math.pow(1 - clamp(p), 3),
    in: (p) => Math.pow(clamp(p), 3),
  };
  const pegaEase = (e) => (typeof e === 'function' ? e : EASE[e] || (window.EdinVideo && window.EdinVideo.ease[e]) || suave);

  // ------------------------------------------------------------------ aleatório com semente
  function hash(i, s = 0) {
    let h = (Math.imul(i | 0, 0x27d4eb2d) ^ Math.imul(s | 0, 0x165667b1)) >>> 0;
    h = Math.imul(h ^ (h >>> 15), 0x85ebca6b) >>> 0;
    h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35) >>> 0;
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  }
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
  // ruído suave 1D em [-1, 1]
  function ruido(x, s) {
    const i = Math.floor(x), fr = x - i, u = fr * fr * fr * (fr * (fr * 6 - 15) + 10);
    const g0 = hash(i, s) * 2 - 1, g1 = hash(i + 1, s) * 2 - 1;
    return 2 * lerp(g0 * fr, g1 * (fr - 1), u);
  }
  const embaralha = (s, k) => (Math.imul(s | 0, 7919) + k * 104729) | 0;

  // ------------------------------------------------------------------ cores
  function hex(c) {
    c = c.replace('#', '');
    if (c.length === 3) c = c.split('').map((x) => x + x).join('');
    return [parseInt(c.slice(0, 2), 16), parseInt(c.slice(2, 4), 16), parseInt(c.slice(4, 6), 16)];
  }
  const rgb = (a) => `#${a.map((x) => Math.round(clamp(x, 0, 255)).toString(16).padStart(2, '0')).join('')}`;
  const misturaCor = (a, b, k) => { const A = hex(a), B = hex(b); return rgb(A.map((x, i) => lerp(x, B[i], k))); };
  const escurece = (c, k) => misturaCor(c, '#1a1030', k);
  const clareia = (c, k) => misturaCor(c, '#ffffff', k);

  const PELES = ['#f7d7bf', '#efbf9a', '#dca27a', '#c4875a', '#a26a43', '#7d4e30', '#5c3622', '#3f2418'];
  const CABELOS = ['#1b1416', '#2d1c14', '#4a2c1a', '#6e3f20', '#a5642e', '#d9b36b', '#8f8f96', '#2a1f3d'];
  const ROUPAS = ['#4F46E5', '#7C3AED', '#F97316', '#0f9d8f', '#f2b93b', '#e8e4f4', '#2b2e4a', '#e5484d', '#38a3d6', '#f08aa8', '#6bbf59'];
  const CALCAS = ['#1e1b4b', '#2f3a5c', '#1f2937', '#4a3b5e', '#5b4636', '#c9b28f', '#3a5a8c'];
  const SAPATOS = ['#f4f1ea', '#1f1b2d', '#e5484d', '#4F46E5', '#c9b28f', '#2f2a3a'];
  const PENTEADOS = ['curto', 'crespo', 'cacheado', 'longo', 'coque', 'careca', 'curto', 'longo', 'crespo', 'cacheado'];
  const ROUPAS_TIPO = ['camiseta', 'moletom', 'camisa', 'camiseta', 'moletom'];

  // ------------------------------------------------------------------ geometria (unidade: cabeça)
  // f(): cabeça -> unidade de desenho (100 por cabeça), 1 casa decimal
  const f = (v) => Math.round(v * 1000) / 10;
  const baixo = (a) => [Math.sin(a * RAD), Math.cos(a * RAD)];     // membro: 0 = para baixo, + para a frente
  const cima = (a) => [Math.sin(a * RAD), -Math.cos(a * RAD)];
  const mais = (p, d, k = 1) => [p[0] + d[0] * k, p[1] + d[1] * k];
  const meio = (a, b, k = 0.5) => [lerp(a[0], b[0], k), lerp(a[1], b[1], k)];
  const angPara = (a, b) => Math.atan2(b[0] - a[0], b[1] - a[1]) / RAD; // ângulo de membro de a até b
  // referencial local (x para a frente, y para cima) girado de a graus, origem O, na tela (y para baixo)
  function quadroLocal(O, a) {
    const c = Math.cos(a * RAD), s = Math.sin(a * RAD);
    return (x, y) => [O[0] + x * c + y * s, O[1] + x * s - y * c];
  }
  // referencial de membro: u ao longo do membro (ângulo a), v para a frente (lado n) vezes lado
  function quadroMembro(O, a, lado = 1) {
    const u = baixo(a), v = [u[1] * lado, -u[0] * lado];
    return (x, y) => [O[0] + u[0] * x + v[0] * y, O[1] + u[1] * x + v[1] * y];
  }

  // círculo no sentido horário (todas as formas no mesmo sentido: a união com nonzero nunca fura)
  function circ(c, r) {
    return `M${f(c[0] - r)} ${f(c[1])}A${f(r)} ${f(r)} 0 1 1 ${f(c[0] + r)} ${f(c[1])}A${f(r)} ${f(r)} 0 1 1 ${f(c[0] - r)} ${f(c[1])}Z`;
  }
  // membro afunilado com bojo: A (raio ra) até B (raio rb); rm1 = bojo do lado da frente, rm2 = do lado de trás
  function membro(A, B, ra, rb, rm1, rm2, pico = 0.5) {
    let dx = B[0] - A[0], dy = B[1] - A[1];
    let L = Math.hypot(dx, dy);
    if (L < 1e-5) { dx = 0; dy = 1e-5; L = 1e-5; }
    const ux = dx / L, uy = dy / L, nx = uy, ny = -ux;
    const a1x = A[0] + nx * ra, a1y = A[1] + ny * ra, b1x = B[0] + nx * rb, b1y = B[1] + ny * rb;
    const b2x = B[0] - nx * rb, b2y = B[1] - ny * rb, a2x = A[0] - nx * ra, a2y = A[1] - ny * ra;
    const mx = A[0] + dx * pico, my = A[1] + dy * pico, base = (ra + rb) / 2;
    let s = `M${f(a1x)} ${f(a1y)}`;
    if (rm1 == null) s += `L${f(b1x)} ${f(b1y)}`;
    else { const h = 2 * rm1 - base; s += `Q${f(mx + nx * h)} ${f(my + ny * h)} ${f(b1x)} ${f(b1y)}`; }
    s += `A${f(rb)} ${f(rb)} 0 0 1 ${f(b2x)} ${f(b2y)}`;
    if (rm2 == null) s += `L${f(a2x)} ${f(a2y)}`;
    else { const h = 2 * rm2 - base; s += `Q${f(mx - nx * h)} ${f(my - ny * h)} ${f(a2x)} ${f(a2y)}`; }
    return s + `A${f(ra)} ${f(ra)} 0 0 1 ${f(a1x)} ${f(a1y)}Z`;
  }
  // curva fechada suave (Catmull-Rom) por pontos na tela; [x, y, 1] = canto vivo. Sempre no sentido horário.
  function fechado(P) {
    const n = P.length;
    let area = 0;
    for (let i = 0; i < n; i++) { const a = P[i], b = P[(i + 1) % n]; area += a[0] * b[1] - b[0] * a[1]; }
    if (area < 0) P = P.slice().reverse();
    let s = `M${f(P[0][0])} ${f(P[0][1])}`;
    for (let i = 0; i < n; i++) {
      const p0 = P[(i - 1 + n) % n], p1 = P[i], p2 = P[(i + 1) % n], p3 = P[(i + 2) % n];
      const k1 = p1[2] ? 0 : 1 / 6, k2 = p2[2] ? 0 : 1 / 6;
      s += `C${f(p1[0] + (p2[0] - p0[0]) * k1)} ${f(p1[1] + (p2[1] - p0[1]) * k1)} ${f(p2[0] - (p3[0] - p1[0]) * k2)} ${f(p2[1] - (p3[1] - p1[1]) * k2)} ${f(p2[0])} ${f(p2[1])}`;
    }
    return s + 'Z';
  }
  // polilinha aberta suave (para traços de detalhe)
  function aberta(P) {
    const n = P.length;
    let s = `M${f(P[0][0])} ${f(P[0][1])}`;
    if (n === 2) return s + `L${f(P[1][0])} ${f(P[1][1])}`;
    for (let i = 0; i < n - 1; i++) {
      const p0 = P[Math.max(0, i - 1)], p1 = P[i], p2 = P[i + 1], p3 = P[Math.min(n - 1, i + 2)];
      s += `C${f(p1[0] + (p2[0] - p0[0]) / 6)} ${f(p1[1] + (p2[1] - p0[1]) / 6)} ${f(p2[0] - (p3[0] - p1[0]) / 6)} ${f(p2[1] - (p3[1] - p1[1]) / 6)} ${f(p2[0])} ${f(p2[1])}`;
    }
    return s;
  }
  // mistura de listas de pontos [x, y(, canto)]
  const mistPts = (A, B, k) => A.map((p, i) => (p[2] ? [lerp(p[0], B[i][0], k), lerp(p[1], B[i][1], k), 1] : [lerp(p[0], B[i][0], k), lerp(p[1], B[i][1], k)]));

  // ------------------------------------------------------------------ proporções (cabeças)
  const PR = { lombar: 1.1, dorso: 1.22, pescoco: 0.36, braco: 1.42, antebraco: 1.22, coxa: 1.9, canela: 1.78 };

  // cabeça: perfil (olhando para +x) e frente, mesmos índices; origem no topo do pescoço, y para cima
  const CAB_PERFIL = [[-0.2, 0.06], [-0.4, 0.3], [-0.45, 0.56], [-0.34, 0.82], [-0.08, 0.93], [0.2, 0.88], [0.35, 0.71], [0.39, 0.57],
    [0.36, 0.5], [0.47, 0.35], [0.40, 0.3], [0.42, 0.25], [0.385, 0.2], [0.41, 0.155], [0.355, 0.085], [0.375, 0.0], [0.28, -0.07], [0.08, -0.04], [-0.05, 0.05]];
  const CAB_FRENTE = [[-0.17, 0.02], [-0.31, 0.24], [-0.37, 0.52], [-0.31, 0.8], [-0.08, 0.93], [0.15, 0.91], [0.3, 0.8], [0.36, 0.62],
    [0.37, 0.5], [0.36, 0.4], [0.345, 0.32], [0.325, 0.25], [0.3, 0.18], [0.27, 0.12], [0.23, 0.06], [0.17, 0.0], [0.09, -0.06], [0.0, -0.08], [-0.09, -0.05]];

  // cabelo (no referencial da cabeça). 'frente' fica por cima da cabeça, 'atras' atrás dela.
  const CAP_PERFIL = [[0.35, 0.69], [0.31, 0.86], [0.1, 0.995], [-0.22, 0.985], [-0.46, 0.8], [-0.52, 0.52], [-0.44, 0.2], [-0.26, 0.2], [-0.15, 0.48], [0.05, 0.6], [0.22, 0.67]];
  const CAP_FRENTE = [[0.38, 0.5], [0.42, 0.77], [0.24, 0.99], [-0.06, 1.035], [-0.33, 0.94], [-0.43, 0.7], [-0.385, 0.47], [-0.34, 0.6], [-0.18, 0.74], [0.06, 0.77], [0.3, 0.66]];
  const LONGO_PERFIL = [[0.05, 1.0], [-0.33, 0.93], [-0.55, 0.62], [-0.58, 0.1], [-0.6, -0.5], [-0.5, -1.05], [-0.22, -0.98], [-0.17, -0.4], [-0.12, 0.1], [0.08, 0.5]];
  const LONGO_FRENTE = [[0.0, 1.04], [-0.39, 0.93], [-0.5, 0.55], [-0.52, 0.0], [-0.55, -0.45], [-0.42, -0.74], [0.42, -0.74], [0.55, -0.45], [0.52, 0.0], [0.43, 0.76]];

  // volume crespo/cacheado: elipse com ondulação (pontos gerados uma vez)
  function volume(cx, cy, rx, ry, n, amp, fase = 0) {
    const P = [];
    for (let i = 0; i < n; i++) {
      const a = (i / n) * TAU;
      const r = 1 + amp * (i % 2 ? -0.5 : 1) * (0.8 + 0.4 * Math.sin(i * 1.7 + fase));
      P.push([cx + Math.cos(a) * rx * r, cy + Math.sin(a) * ry * r]);
    }
    return P;
  }
  const CRESPO_PERFIL = volume(-0.12, 0.6, 0.66, 0.6, 26, 0.06);
  const CRESPO_FRENTE = volume(0, 0.64, 0.7, 0.6, 26, 0.06);
  const CACHO_PERFIL = volume(-0.17, 0.4, 0.55, 0.66, 30, 0.07, 1);
  const CACHO_FRENTE = volume(0, 0.42, 0.57, 0.64, 30, 0.07, 1);
  const FRANJA_CACHO_P = volume(0.0, 0.8, 0.42, 0.22, 16, 0.12, 2);
  const FRANJA_CACHO_F = volume(0.0, 0.84, 0.4, 0.2, 16, 0.12, 2);

  // pé/sapato (referencial do pé: x para a frente, y para baixo, origem no tornozelo)
  const PE_PERFIL = [[-0.12, -0.14], [0.1, -0.13], [0.38, 0.0], [0.72, 0.07], [0.87, 0.18], [0.8, 0.27], [0.3, 0.28], [-0.17, 0.27], [-0.24, 0.12], [-0.2, -0.02]];
  const PE_FRENTE = [[-0.11, -0.14], [0.11, -0.14], [0.15, 0.0], [0.18, 0.1], [0.17, 0.2], [0.12, 0.28], [0.0, 0.29], [-0.12, 0.28], [-0.18, 0.18], [-0.16, 0.02]];
  const SOLA_PERFIL = [[-0.2, 0.19, 1], [0.3, 0.2], [0.85, 0.19, 1], [0.8, 0.27], [0.3, 0.28], [-0.17, 0.27]];
  const SOLA_FRENTE = [[-0.17, 0.2, 1], [0.0, 0.21], [0.17, 0.2, 1], [0.12, 0.28], [0.0, 0.29], [-0.12, 0.28]];

  // ------------------------------------------------------------------ pose
  const POSE0 = {
    giro: 0.5, tronco: 0, peito: 0, pescoco: 0, cabeca: 0, ombros: 0,
    oP: 0, cP: 10, mP: 0, oL: 0, cL: 10, mL: 0,
    qP: 0, jP: 2, tP: 0, qL: 0, jL: 2, tL: 0, peNivel: 1,
    fechaP: 0.3, apontaP: 0, abreP: 0, vistaP: 0.25, ladoP: 1,
    fechaL: 0.3, apontaL: 0, abreL: 0, vistaL: 0.25, ladoL: 1,
    ikP: 0, ikPx: 0, ikPy: 0, dobraP: 1, ikL: 0, ikLx: 0, ikLy: 0, dobraL: 1,
    mAbsP: 0, mAngP: 90, mAbsL: 0, mAngL: 90,
    sentado: 0, alt: 2.05, voo: 0, dx: 0,
    celular: 0, caneta: 0, cadeira: 0, mesa: 0, degraus: 0, escreve: 0,
    olhos: 1, boca: 0, vivo: 1, sentidoEscrita: 1,
  };
  const pose0 = (o) => Object.assign({}, POSE0, o);

  const POSES = {
    'em-pe': pose0({ giro: 0.55, peito: -2, pescoco: 2, cabeca: -2, oP: -5, cP: 12, oL: 7, cL: 14, qP: 2, jP: 2, qL: -3, jL: 10, tL: 0,
      fechaP: 0.35, fechaL: 0.35, vistaP: 0.35, vistaL: 0.35 }),
    'cabeca-baixa': pose0({ giro: 0.42, tronco: 2, peito: 13, pescoco: 20, cabeca: 22, ombros: -0.6, oP: 7, cP: 10, oL: 4, cL: 9,
      qP: 1, jP: 2, qL: -3, jL: 6, fechaP: 0.2, fechaL: 0.2, boca: -0.8, olhos: 0.55 }),
    'olhando-celular': pose0({ giro: 0.3, tronco: 1, peito: 7, pescoco: 15, cabeca: 16, oP: 8, cP: 96, mP: -22, fechaP: 0.62, vistaP: 0.1,
      celular: 1, oL: 3, cL: 14, qP: 3, jP: 2, qL: -4, jL: 9, olhos: 0.8 }),
    'punho-erguido': pose0({ giro: 0.85, peito: -4, pescoco: -2, cabeca: -9, oP: -168, cP: -10, mP: -4, fechaP: 1, vistaP: 1, ladoP: -1,
      oL: 9, cL: 14, fechaL: 0.45, qP: -5, jP: 2, qL: 5, jL: 2, boca: 0.3 }),
    'bracos-abertos': pose0({ giro: 1, peito: -6, pescoco: -4, cabeca: -11, oP: -98, cP: -10, mP: -6, abreP: 1, fechaP: 0, vistaP: 1, ladoP: -1,
      oL: 98, cL: 10, mL: 6, abreL: 1, fechaL: 0, vistaL: 1, qP: -5, qL: 5, boca: 0.8 }),
    'apontando': pose0({ giro: 0.2, tronco: 2, peito: -3, pescoco: -1, cabeca: -3, oP: 84, cP: 5, mP: 3, fechaP: 1, apontaP: 1, vistaP: 0.2,
      oL: -5, cL: 14, qP: 9, jP: 3, qL: -11, jL: 6 }),
    'olhando-horizonte': pose0({ giro: 0.18, tronco: -1, peito: -3, pescoco: -2, cabeca: -6, ikP: 1, ikPx: 0.12, ikPy: 3.3, dobraP: -1,
      mAbsP: 1, mAngP: 100, fechaP: 0.12, vistaP: 0.3, oL: -3, cL: 12, qP: 5, jP: 2, qL: -7, jL: 5 }),
    'subindo': pose0({ giro: 0.15, tronco: 13, peito: 3, pescoco: -2, cabeca: -8, qP: 60, jP: 76, tP: -2, qL: -14, jL: 12, tL: 26,
      oP: -24, cP: 28, oL: 30, cL: 40, fechaP: 0.55, fechaL: 0.55, degraus: 1 }),
    'sentado-estudando': pose0({ giro: 0.12, sentado: 1, alt: 2.2, tronco: 12, peito: 10, pescoco: 12, cabeca: 18,
      qP: 84, jP: 88, tP: 0, qL: 80, jL: 84, tL: 0,
      ikP: 1, ikPx: 2.0, ikPy: 1.3, dobraP: -1, mAbsP: 1, mAngP: 128, fechaP: 0.62, vistaP: 0.15, caneta: 1,
      ikL: 1, ikLx: 1.6, ikLy: 1.24, dobraL: -1, mAbsL: 1, mAngL: 96, fechaL: 0.25, vistaL: 0.5,
      cadeira: 1, mesa: 1, escreve: 1, olhos: 0.7 }),
  };

  function mistura(a, b, k, easing) {
    const e = easing === false ? clamp(k) : pegaEase(easing || 'suave')(k);
    const o = {};
    for (const key in POSE0) {
      const va = a[key] != null ? a[key] : POSE0[key], vb = b[key] != null ? b[key] : POSE0[key];
      o[key] = va + (vb - va) * e;
    }
    o.avanco = lerp(a.avanco || 0, b.avanco || 0, e);
    return o;
  }

  // gaussiana periódica em torno de c (largura w, em radianos)
  const bump = (x, c, w) => { let d = (x - c) % TAU; if (d > Math.PI) d -= TAU; if (d < -Math.PI) d += TAU; return Math.exp(-(d * d) / (2 * w * w)); };

  // ciclos procedurais. t em s; velocidade multiplica a cadência; fase em voltas (0 a 1)
  const CAD = { andando: 0.95, correndo: 1.38, comemorando: 1.5 };
  function ciclo(nome, t, op = {}) {
    const vel = op.velocidade != null ? op.velocidade : 1, fase = op.fase || 0;
    const cad = (CAD[nome] || 1) * vel;
    const ph = (t * cad + fase) * TAU, s = Math.sin(ph), c2 = Math.cos(2 * ph);
    if (nome === 'andando') {
      const knee = (x) => 5 + 56 * bump(x, -0.55, 0.62) + 10 * bump(x, Math.PI / 2 + 0.55, 0.4);
      const tor = (x) => 16 * bump(x, 1.5 * Math.PI - 0.15, 0.32) - 10 * bump(x, Math.PI / 2 - 0.05, 0.28);
      const o = pose0({
        giro: op.giro != null ? op.giro : 0.12, tronco: 3 + 1.2 * c2, peito: -1, pescoco: 1, cabeca: -1 - 1.2 * c2,
        qP: 2 + 22 * s, qL: 2 - 22 * s, jP: knee(ph), jL: knee(ph + Math.PI), tP: tor(ph), tL: tor(ph + Math.PI), peNivel: 1,
        oP: 3 - 21 * s, oL: 3 + 21 * s, cP: 14 + 16 * clamp(-s), cL: 14 + 16 * clamp(s), fechaP: 0.35, fechaL: 0.35, vistaP: 0.2, vistaL: 0.2,
        ombros: 0.15 * c2,
      });
      o.avanco = AVANCO.andando * (t * cad + fase);
      return o;
    }
    if (nome === 'correndo') {
      const knee = (x) => 18 + 92 * bump(x, -0.35, 0.85) + 20 * bump(x, Math.PI + 0.25, 0.45);
      const tor = (x) => 22 * bump(x, 1.5 * Math.PI - 0.2, 0.4) + 6;
      const o = pose0({
        giro: op.giro != null ? op.giro : 0.08, tronco: 12 + 1.5 * c2, peito: 1, pescoco: -3, cabeca: -8 - 1.5 * c2,
        qP: 8 + 38 * s, qL: 8 - 38 * s, jP: knee(ph), jL: knee(ph + Math.PI), tP: tor(ph), tL: tor(ph + Math.PI), peNivel: 0.35,
        oP: -8 - 42 * s, oL: -8 + 42 * s, cP: 84 - 20 * s, cL: 84 + 20 * s, mP: -5, mL: -5, fechaP: 1, fechaL: 1, vistaP: 0.15, vistaL: 0.15,
        voo: 0.16 * Math.max(0, -Math.cos(2 * ph + 0.5)) - 0.05, ombros: 0.2 * c2, boca: 0.2,
      });
      o.avanco = AVANCO.correndo * (t * cad + fase);
      return o;
    }
    if (nome === 'comemorando') {
      const pulo = Math.abs(Math.sin(ph / 2)), b = Math.sin(ph);
      return pose0({
        giro: op.giro != null ? op.giro : 0.9, peito: -6, pescoco: -3, cabeca: -10 + 3 * b,
        oP: -148 + 12 * b, cP: -22 - 10 * b, oL: 148 - 12 * b, cL: 22 + 10 * b, fechaP: 1, fechaL: 1, vistaP: 1, vistaL: 1, ladoP: -1,
        qP: -6 + 10 * (1 - pulo), jP: 8 + 34 * (1 - pulo), qL: 6 + 10 * (1 - pulo), jL: 8 + 34 * (1 - pulo), tP: 12 * pulo, tL: 12 * pulo,
        voo: 0.42 * pulo, boca: 1,
      });
    }
    return pose(nome);
  }
  // distância percorrida por volta do ciclo (cabeças), medida pelo pé de apoio (calculada no carregamento)
  const AVANCO = { andando: 5.9, correndo: 7.5 };

  // pose pelo nome no instante t (ciclos animam; poses fixas devolvem uma cópia)
  function pose(nome, t = 0, op = {}) {
    if (nome && typeof nome === 'object') return pose0(nome);
    if (nome === 'andando' || nome === 'correndo' || nome === 'comemorando') return ciclo(nome, t, op);
    const p = POSES[nome];
    if (!p) { console.warn(`[edin-pessoas] pose desconhecida "${nome}"`); return pose0({}); }
    return Object.assign({}, p);
  }

  // piscar determinístico: uma piscada a cada ~2,6 a 4,6 s, 0,15 s de duração
  function piscar(t, sem) {
    const P = 3.6, i = Math.floor(t / P);
    let k = 0;
    for (let j = i - 1; j <= i + 1; j++) {
      const tb = j * P + 0.4 + hash(j, sem) * 2.6;
      k = Math.max(k, 1 - Math.abs(t - tb) / 0.075);
      if (hash(j, sem + 9) < 0.18) k = Math.max(k, 1 - Math.abs(t - tb - 0.3) / 0.075); // às vezes pisca duas vezes
    }
    return suave(k);
  }

  // vida sempre ligada: respiração, balanço de peso, cabeça e braços com ruído lento, piscar, escrever
  function vivo(p, t, sem, forca = 1) {
    const q = Object.assign({}, p);
    const F = forca * (p.vivo != null ? p.vivo : 1);
    const resp = Math.sin(TAU * (t / 3.7) + hash(1, sem) * 6.28);
    q.peito += 1.0 * resp * F; q.ombros += 0.3 * resp * F; q.cabeca -= 0.5 * resp * F;
    q.tronco += 0.8 * ruido(t * 0.16, sem + 1) * F;
    q.cabeca += 2.2 * ruido(t * 0.22, sem + 2) * F;
    q.pescoco += 1.0 * ruido(t * 0.18, sem + 3) * F;
    q.oP += 1.8 * ruido(t * 0.3, sem + 4) * F; q.oL += 1.8 * ruido(t * 0.3, sem + 5) * F;
    q.cP += 2.0 * ruido(t * 0.27, sem + 6) * F; q.cL += 2.0 * ruido(t * 0.27, sem + 7) * F;
    q.fechaP = clamp(q.fechaP + 0.05 * ruido(t * 0.4, sem + 8) * F); q.fechaL = clamp(q.fechaL + 0.05 * ruido(t * 0.4, sem + 10) * F);
    q.olhos = q.olhos * (1 - piscar(t, sem));
    if (q.escreve > 0) {
      const e = q.escreve;
      // a mão anda pela linha (volta a cada 3,2 s) e sobe e desce nas letras
      const linha = (t / 3.2) % 1;
      // letras: laços (x volta um pouco a cada letra) e altura variável; palavra a palavra (pausa entre elas)
      const fl = TAU * 2.4 * t, alto = 0.6 + 0.4 * Math.abs(Math.sin(t * 1.7));
      const palavra = 0.5 + 0.5 * Math.cos(TAU * t / 1.6);
      const sd = q.sentidoEscrita >= 0 ? 1 : -1;
      q.ikPx += e * (sd * (0.62 * linha - 0.3) + 0.035 * Math.sin(fl) * palavra);
      q.ikPy += e * (0.06 * alto * Math.cos(fl) * palavra);
      q.mAngP += e * 2.5 * Math.sin(fl + 0.6);
      q.cabeca += e * 3 * (linha - 0.5);
    }
    return q;
  }

  // ------------------------------------------------------------------ corpo (aparência)
  function corpoPadrao(tipo = 'a', r = null) {
    const j = (a) => (r ? (r() - 0.5) * a : 0);
    const b = tipo === 'b'
      ? { om: 0.86, ci: 0.56, qu: 0.76, pe: 0.5, ba: 0.34, gl: 0.47, gr: 0.95 }
      : { om: 0.98, ci: 0.63, qu: 0.69, pe: 0.48, ba: 0.36, gl: 0.42, gr: 1.03 };
    const larg = 1 + j(0.16);
    return { om: b.om * larg, ci: (b.ci + j(0.12)) * larg, qu: (b.qu + j(0.08)) * larg, pe: b.pe + j(0.06), ba: b.ba + j(0.1), gl: b.gl + j(0.05), gr: b.gr * (1 + j(0.14)) };
  }

  function aparencia(semente = 1, op = {}) {
    const r = aleatorio(semente * 31 + 7);
    const tipo = op.corpoTipo || (r() < 0.5 ? 'a' : 'b');
    const ap = {
      pele: PELES[Math.floor(r() * PELES.length)],
      cabelo: PENTEADOS[Math.floor(r() * PENTEADOS.length)],
      corCabelo: CABELOS[Math.floor(r() * 6)],
      roupa: ROUPAS_TIPO[Math.floor(r() * ROUPAS_TIPO.length)],
      corRoupa: ROUPAS[Math.floor(r() * ROUPAS.length)],
      corCalca: CALCAS[Math.floor(r() * CALCAS.length)],
      corSapato: SAPATOS[Math.floor(r() * SAPATOS.length)],
      mochila: r() < 0.3, corMochila: ROUPAS[Math.floor(r() * ROUPAS.length)],
      oculos: r() < 0.25,
      corpoTipo: tipo,
    };
    ap.corpo = corpoPadrao(tipo, r);
    ap.escala = 0.92 + r() * 0.14;
    if (ap.corRoupa === ap.corMochila) ap.corMochila = '#2b2e4a';
    Object.assign(ap, op);
    if (op.corpo && typeof op.corpo === 'object') ap.corpo = Object.assign(corpoPadrao(tipo), op.corpo);
    return ap;
  }

  // ------------------------------------------------------------------ cinemática
  function ik2(S, T, L1, L2, dobra) {
    let dx = T[0] - S[0], dy = T[1] - S[1];
    let d = Math.hypot(dx, dy);
    const dmax = L1 + L2 - 1e-3, dmin = Math.abs(L1 - L2) + 1e-3;
    if (d > dmax) { dx *= dmax / d; dy *= dmax / d; d = dmax; }
    if (d < dmin) { d = dmin; }
    const th = Math.atan2(dx, dy) / RAD;
    const al = Math.acos(clamp((L1 * L1 + d * d - L2 * L2) / (2 * L1 * d), -1, 1)) / RAD;
    const aU = th + (dobra >= 0 ? al : -al);
    const E = mais(S, baixo(aU), L1);
    return [aU, angPara(E, [S[0] + dx, S[1] + dy])];
  }
  const lerpAng = (a, b, k) => { let d = (b - a) % 360; if (d > 180) d -= 360; if (d < -180) d += 360; return a + d * k; };

  // calcula as juntas (tela, cabeças, chão em y = 0, x = 0 no quadril)
  function rig(p, c, olhar) {
    const J = {};
    const g = clamp(p.giro);
    // pernas a partir do quadril (ângulos absolutos)
    function pernas(P) {
      const a1 = p.tronco, TL = quadroLocal(P, a1);
      const r = {};
      for (const L of ['P', 'L']) {
        const sg = L === 'P' ? -1 : 1;
        const H = TL(lerp(0.03 * sg, sg * c.qu * 0.5, g), 0);
        const aT = p['q' + L], K = mais(H, baixo(aT), PR.coxa);
        const aS = aT - p['j' + L], A = mais(K, baixo(aS), PR.canela);
        const af = lerp(aS + 90 - p['t' + L], 90 - p['t' + L], p.peNivel);
        const afF = lerp(af, aS + 90, g); // de frente, o pé aponta para a câmera
        r[L] = { H, K, A, aT, aS, af: afF };
      }
      return r;
    }
    // chão: ponto mais baixo da sola dos dois pés
    const pe0 = pernas([0, 0]);
    let maxY = -1e9;
    for (const L of ['P', 'L']) {
      const e = pe0[L], fr = quadroPe(e.A, e.af);
      for (const q of [mistPts([PE_PERFIL[5], PE_PERFIL[6], PE_PERFIL[7], PE_PERFIL[4]], [PE_FRENTE[5], PE_FRENTE[6], PE_FRENTE[7], PE_FRENTE[4]], g)]) {
        for (const pt of q) { const w = fr(pt[0], pt[1]); if (w[1] > maxY) maxY = w[1]; }
      }
    }
    const yAuto = -maxY, yFix = -p.alt;
    const P = [p.dx, lerp(yAuto, Math.min(yFix, yAuto), clamp(p.sentado)) - Math.max(-0.2, p.voo)];
    J.P = P; J.chaoAuto = yAuto;
    const pe = pernas(P);
    J.pernas = pe;

    // tronco em dois segmentos
    const a1 = p.tronco, a2 = p.tronco + p.peito, a3 = a2 + p.pescoco;
    const TL = quadroLocal(P, a1), Wc = TL(0, PR.lombar), TU = quadroLocal(Wc, a2);
    J.a1 = a1; J.a2 = a2; J.a3 = a3; J.TL = TL; J.TU = TU; J.W = Wc;
    const N = TU(lerp(-0.03, 0, g), PR.dorso);
    const Hd = mais(N, cima(a3), PR.pescoco);
    J.N = N; J.Hd = Hd;
    let ah = a3 + p.cabeca, gc = g;
    if (olhar) {
      const w = olhar.peso != null ? olhar.peso : 1;
      const ex = mais(Hd, cima(ah), 0.5);
      const vx = olhar.x - ex[0], vy = olhar.y - ex[1];
      if (vx > 0.05) {
        const des = Math.atan2(vy, vx) / RAD;
        const rel = clamp(des - a3, -40, 35);
        ah = lerpAng(ah, a3 + rel, w * clamp(1 - g * 0.8));
      }
      // de frente, olhar para o lado vira a cabeça para o perfil
      gc = lerp(g, g * 0.35, w * clamp(Math.abs(vx) / 3) * (vx > 0 ? 1 : 0));
    }
    J.ah = ah; J.gc = gc;

    // braços
    const sx = c.om - 0.17, sy = PR.dorso - 0.26 + p.ombros * 0.06;
    J.bracos = {};
    for (const L of ['P', 'L']) {
      const sg = L === 'P' ? -1 : 1;
      const S = TU(lerp(0.0 * sg, sg * sx, g), sy);
      let aU = a2 + p['o' + L], aF = aU + p['c' + L];
      const k = clamp(p['ik' + L]);
      if (k > 0) {
        const T = [P[0] + p['ik' + L + 'x'], P[1] - p['ik' + L + 'y']];
        const [u2, f2] = ik2(S, T, PR.braco, PR.antebraco, p['dobra' + L]);
        aU = lerpAng(aU, u2, k); aF = lerpAng(aF, f2, k);
      }
      const E = mais(S, baixo(aU), PR.braco), Wr = mais(E, baixo(aF), PR.antebraco);
      let aM = aF + p['m' + L];
      if (p['mAbs' + L] > 0) aM = lerpAng(aM, p['mAng' + L], clamp(p['mAbs' + L]));
      J.bracos[L] = { S, E, Wr, aU, aF, aM };
    }
    return J;
  }
  function quadroPe(A, af) {
    const fd = baixo(af), dn = [-fd[1], fd[0]];
    return (x, y) => [A[0] + fd[0] * x + dn[0] * y, A[1] + fd[1] * x + dn[1] * y];
  }

  // ------------------------------------------------------------------ desenho das partes
  // Coletor: camadas (ordem de pintura) x materiais. Estilos leem daqui.
  const CAM = { MOVEL: 0, CAB_ATRAS: 1, BRACO_L: 2, PERNA_L: 3, PERNA_P: 4, MESA: 5, MOCHILA: 6, TRONCO: 7, CABECA: 8, CAB_FRENTE: 9, ACESS: 10, BRACO_P: 11 };
  const N_CAM = 12;
  const MATS = [
    ['movelEscuro', 'movel'],
    ['cabelo'],
    ['pele', 'roupa', 'objeto', 'tela'],
    ['calca', 'sapato', 'sola'],
    ['calca', 'sapato', 'sola'],
    ['movelEscuro', 'movel', 'papel', 'livro', 'livro2', 'objeto', 'luz'],
    ['mochila'],
    ['peleEscura', 'calca', 'roupa'],
    ['pele', 'peleEscura'],
    ['cabelo'],
    ['mochila', 'oculos'],
    ['pele', 'roupa', 'objeto', 'tela'],
  ];
  // traços de detalhe: 'linha' (traço), 'olho' (preenchido escuro), 'brilho' (claro)
  const DETALHES = ['linha', 'olho', 'brilho'];
  function coletor() {
    const c = { s: [], d: [], luzes: [] };
    c.limpar = () => {
      for (let i = 0; i < N_CAM; i++) { c.s[i] = {}; c.d[i] = {}; }
      c.luzes.length = 0; c.caneta = null; c.celular = null;
    };
    c.add = (cam, mat, d) => { c.s[cam][mat] = (c.s[cam][mat] || '') + d; };
    c.det = (cam, mat, d) => { c.d[cam][mat] = (c.d[cam][mat] || '') + d; };
    c.limpar();
    return c;
  }

  // mão com palma e dedos. m: { fecha, aponta, abre, vista, lado }
  function mao(col, cam, mat, Wr, ang, m, esc = 1, detalhe = false) {
    const ld = m.lado >= 0 ? 1 : -1, vi = clamp(m.vista);
    const F = quadroMembro(Wr, ang, ld);
    const e = esc;
    const wW = lerp(0.078, 0.1, vi) * e, wK = lerp(0.09, 0.145, vi) * e;
    // palma (com o volume do polegar)
    col.add(cam, mat, fechado([F(-0.02 * e, wW), F(0.14 * e, wK * 1.12), F(0.3 * e, wK), F(0.34 * e, 0), F(0.3 * e, -wK), F(0.12 * e, -wK * 1.02), F(-0.02 * e, -wW)]));
    const fecha = clamp(m.fecha), abre = clamp(m.abre), ap = clamp(m.aponta);
    const lens = [0.36, 0.4, 0.37, 0.29], rs = [0.043, 0.044, 0.042, 0.037], bases = [];
    const offL = [0.035, 0.012, -0.012, -0.035], offF = [0.105, 0.035, -0.035, -0.105];
    const sp = [11, 3.5, -4, -12];
    for (let i = 0; i < 4; i++) {
      const c = fecha * (i === 0 ? 1 - ap : 1);
      const base = F(0.29 * e, lerp(offL[i], offF[i] * (wK / (0.145 * e)), vi) * e);
      const rot = c * lerp(1, 0.0, vi), ls = lerp(1 - 0.42 * c, 1 - 0.74 * c, vi);
      const a1 = ang + ld * sp[i] * (0.3 + abre * 0.75) - ld * rot * 88;
      const L = lens[i] * e * ls, r = rs[i] * e * lerp(1.12, 1.08, vi) * (1 + 0.3 * c);
      const j1 = mais(base, baixo(a1), L * 0.56);
      const a2 = a1 - ld * rot * 105;
      const tip = mais(j1, baixo(a2), L * 0.44);
      bases.push([base, tip]);
      col.add(cam, mat, membro(base, j1, r, r * 0.94));
      col.add(cam, mat, membro(j1, tip, r * 0.94, r * 0.84));
    }
    // polegar
    const tb = F(lerp(0.07, 0.17, vi * fecha) * e, lerp(wW * 0.85, wK * 0.95, vi * fecha));
    const aOpen = ang + ld * (32 + 26 * abre);
    const aClose = ang - ld * lerp(18, 58, vi);
    const t1 = lerpAng(aOpen, aClose, fecha * (1 - 0.3 * ap));
    const p1 = mais(tb, baixo(t1), lerp(0.2, 0.15, vi * fecha) * e);
    const t2 = t1 - ld * fecha * lerp(45, 38, vi);
    const p2 = mais(p1, baixo(t2), lerp(0.16, 0.12, vi * fecha) * e);
    col.add(cam, mat, membro(tb, p1, 0.058 * e, 0.05 * e));
    col.add(cam, mat, membro(p1, p2, 0.05 * e, 0.043 * e));
    // punho de frente: vãos entre os dedos dobrados e a borda do polegar por cima deles
    const kf = clamp((vi - 0.5) * 2) * clamp((fecha - 0.5) * 2);
    if (kf > 0.5 && esc > 0.9) {
      for (let i = 0; i < 3; i++) {
        const a = meio(bases[i][0], bases[i + 1][0]), b = meio(bases[i][1], bases[i + 1][1]);
        col.det(cam, 'linha', aberta([mais(a, baixo(ang), 0.02 * e), meio(a, b, 0.75)]));
      }
      col.det(cam, 'linha', aberta([mais(tb, baixo(t1 + 90 * ld), 0.05 * e), mais(p1, baixo(t1 + 90 * ld), 0.05 * e), mais(p2, baixo(t2 + 90 * ld), 0.045 * e)]));
    }
    return F;
  }

  // caneta presa entre polegar e indicador: [traseira, ponta]
  function caneta(b, lado, e, k = 1) {
    const F = quadroMembro(b.Wr, b.aM, lado >= 0 ? 1 : -1), a = b.aM - 52 * (lado >= 0 ? 1 : -1);
    const base = F(0.31 * e, 0.02 * e);
    return [mais(base, baixo(a), -0.26 * k), mais(base, baixo(a), 0.42 * k)];
  }
  // braço completo (pele + manga + mão + objetos)
  function braco(col, cam, b, L, p, ap, c, matPele) {
    const gr = c.gr;
    const { S, E, Wr, aM } = b;
    col.add(cam, matPele, membro(S, E, 0.19 * gr, 0.125 * gr, 0.185 * gr, 0.175 * gr, 0.35));
    col.add(cam, matPele, membro(E, Wr, 0.125 * gr, 0.085 * gr, 0.145 * gr, 0.135 * gr, 0.3));
    const m = { fecha: p['fecha' + L], aponta: p['aponta' + L], abre: p['abre' + L], vista: p['vista' + L], lado: p['lado' + L] };
    const F = mao(col, cam, matPele, Wr, aM, m, 1.14 * gr);
    // manga
    const r = ap.roupa;
    if (r === 'camiseta') col.add(cam, 'roupa', membro(S, meio(S, E, 0.52), 0.23 * gr, 0.18 * gr, 0.225 * gr, 0.215 * gr));
    else if (r === 'moletom') {
      col.add(cam, 'roupa', membro(S, E, 0.24 * gr, 0.16 * gr, 0.22 * gr, 0.215 * gr, 0.4));
      col.add(cam, 'roupa', membro(E, meio(E, Wr, 0.9), 0.16 * gr, 0.125 * gr, 0.165 * gr, 0.16 * gr, 0.35));
    } else if (r === 'camisa') {
      col.add(cam, 'roupa', membro(S, E, 0.23 * gr, 0.15 * gr, 0.205 * gr, 0.2 * gr, 0.4));
      col.add(cam, 'roupa', membro(E, meio(E, Wr, 0.55), 0.15 * gr, 0.145 * gr, 0.16 * gr, 0.16 * gr));
    }
    // objetos na mão de perto
    if (L === 'P' && p.celular > 0.02) {
      const k = clamp(p.celular), lw = lerp(0.08, 0.32, clamp(p.giro * 1.6)) * k;
      const cx = 0.3, cy = 0.12;
      const Q = [F(cx - lw / 2, cy - 0.3 * k), F(cx + lw / 2, cy - 0.3 * k), F(cx + lw / 2, cy + 0.42 * k), F(cx - lw / 2, cy + 0.42 * k)];
      col.add(cam, 'objeto', fechado(Q.map((q) => [q[0], q[1], 1])));
      if (lw > 0.14) {
        const iw = lw / 2 - 0.025;
        col.add(cam, 'tela', fechado([F(cx - iw, cy - 0.27 * k), F(cx + iw, cy - 0.27 * k), F(cx + iw, cy + 0.36 * k), F(cx - iw, cy + 0.36 * k)].map((q) => [q[0], q[1], 1])));
      }
      const ctr = F(cx, cy + 0.07);
      col.luzes.push({ x: ctr[0], y: ctr[1], k });
      col.celular = { c: ctr, F, cx, cy, lw, k };
    }
    if (L === 'P' && p.caneta > 0.02) {
      const k = clamp(p.caneta);
      const [tail, tip] = caneta(b, p.ladoP, 1.14 * gr, k);
      col.add(cam, 'objeto', membro(tail, tip, 0.03, 0.012));
      col.caneta = tip;
    }
  }

  function perna(col, cam, e, c, ap, g) {
    const gr = c.gr;
    const calf = lerp(0.225, 0.195, g), shin = lerp(0.165, 0.195, g);
    col.add(cam, 'calca', membro(e.H, e.K, 0.37 * gr, 0.205 * gr, 0.35 * gr, 0.33 * gr, 0.35));
    col.add(cam, 'calca', membro(e.K, e.A, 0.205 * gr, 0.135 * gr, (shin + 0.015) * gr, (calf + 0.01) * gr, 0.3));
    const fr = quadroPe(e.A, e.af);
    const pts = mistPts(PE_PERFIL, PE_FRENTE, g).map((q) => fr(q[0], q[1]));
    col.add(cam, 'sapato', fechado(pts));
    col.add(cam, 'sola', fechado(mistPts(SOLA_PERFIL, SOLA_FRENTE, g).map((q) => { const w = fr(q[0], q[1]); return q[2] ? [w[0], w[1], 1] : w; })));
  }

  function tronco(col, J, p, c, ap) {
    const g = clamp(p.giro), TL = J.TL, TU = J.TU;
    const F = [[0.25, 2.34], [c.om - 0.24, 2.25], [c.om, 2.03], [c.om - 0.07, 1.65], [c.ci + 0.07, 1.28], [c.ci, 0.95], [c.qu, 0.38], [c.qu - 0.05, -0.04], [0, -0.2],
      [-(c.qu - 0.05), -0.04], [-c.qu, 0.38], [-c.ci, 0.95], [-(c.ci + 0.07), 1.28], [-(c.om - 0.07), 1.65], [-c.om, 2.03], [-(c.om - 0.24), 2.25], [-0.25, 2.34]];
    const Pf = [[0.15, 2.33], [0.33, 2.18], [c.pe - 0.04, 1.88], [c.pe, 1.6], [c.pe - 0.09, 1.3], [c.ba, 0.95], [c.ba + 0.05, 0.45], [0.3, 0.02], [-0.02, -0.18],
      [-0.36, -0.03], [-c.gl, 0.3], [-0.31, 0.95], [-0.37, 1.3], [-0.44, 1.65], [-0.41, 1.98], [-0.28, 2.22], [-0.12, 2.34]];
    const loc = mistPts(Pf, F, g);
    const T = (x, y) => {
      const w = suave((y - 0.7) / 0.8);
      const a = TL(x, y), b = TU(x, y - PR.lombar);
      return [lerp(a[0], b[0], w), lerp(a[1], b[1], w)];
    };
    const mapa = (L) => L.map((q) => { const w = T(q[0], q[1]); return q[2] ? [w[0], w[1], 1] : w; });
    // pescoço (um pouco mais escuro: dá profundidade sob o queixo)
    const rN = lerp(0.2, 0.165, g) * c.gr;
    col.add(CAM.TRONCO, 'peleEscura', membro(mais(J.N, cima(J.a2), -0.15), mais(J.Hd, cima(J.a3), 0.12), rN, rN * 0.95));
    col.add(CAM.TRONCO, 'calca', fechado(mapa(loc)));
    // camisa até a barra
    const barra = ap.roupa === 'moletom' ? -0.06 : ap.roupa === 'camisa' ? 0.02 : 0.08;
    const cam = loc.map((q) => q.slice());
    cam[7] = [cam[7][0] + 0.04, barra, 1]; cam[8] = [cam[8][0], barra - 0.04]; cam[9] = [cam[9][0] - 0.04, barra, 1];
    // gola: decote acompanha o pescoço
    col.add(CAM.TRONCO, 'roupa', fechado(mapa(cam)));
    if (ap.roupa === 'moletom') {
      // capuz abaixado: volume atrás do pescoço
      const a = T(lerp(-0.4, -0.3, g), lerp(2.22, 2.3, g)), b = T(lerp(-0.12, 0.3, g), lerp(2.42, 2.3, g));
      col.add(CAM.TRONCO, 'roupa', membro(a, b, lerp(0.2, 0.12, g), lerp(0.15, 0.12, g)));
      if (g > 0.4) {
        const k = (g - 0.4) / 0.6;
        col.det(CAM.TRONCO, 'linha', aberta([T(-0.1, 2.26), T(-0.11, 1.95 + 0.05 * (1 - k))]) + aberta([T(0.1, 2.26), T(0.11, 1.95 + 0.05 * (1 - k))]));
        col.det(CAM.TRONCO, 'linha', aberta([T(-c.ci * 0.75, 0.45), T(-c.ci * 0.55, 0.9), T(c.ci * 0.55, 0.9), T(c.ci * 0.75, 0.45)]));
      }
      if (g > 0.4) col.det(CAM.TRONCO, 'linha', aberta([T(-c.qu + 0.04, 0.05), T(0, 0.02), T(c.qu - 0.04, 0.05)]));
    } else if (ap.roupa === 'camisa') {
      col.det(CAM.TRONCO, 'linha', aberta([T(lerp(0.2, 0, g), 2.25), T(lerp(0.27, 0, g), 1.3), T(lerp(0.3, 0, g), barra + 0.05)]));
      col.det(CAM.TRONCO, 'linha', aberta([T(lerp(0.02, -0.2, g), 2.36), T(lerp(0.16, -0.06, g), 2.12), T(lerp(0.22, 0, g), 2.24)]) +
        (g > 0.3 ? aberta([T(0.2, 2.36), T(0.06, 2.12), T(0, 2.24)]) : ''));
    } else {
      col.det(CAM.TRONCO, 'linha', aberta([T(lerp(0.12, -0.2, g), 2.33), T(lerp(0.2, 0, g), lerp(2.18, 2.16, g)), T(lerp(0.3, 0.2, g), 2.33)]));
    }
    // mochila (atrás do tronco) e alças (na frente)
    if (ap.mochila) {
      const a = T(lerp(-0.62, 0, g), 1.25), b = T(lerp(-0.62, 0, g), 1.95);
      col.add(CAM.MOCHILA, 'mochila', membro(a, b, lerp(0.3, 0.46, g), lerp(0.26, 0.42, g)));
      const sgs = g > 0.35 ? [-1, 1] : [1];
      for (const sg of sgs) {
        const x0 = lerp(-0.12, sg * (c.om - 0.42), g), x1 = lerp(0.14, sg * (c.om - 0.38), g), x2 = lerp(-0.1, sg * (c.ci + 0.02), g);
        col.add(CAM.ACESS, 'mochila', membro(T(x0, 2.26), T(x1, lerp(1.86, 1.72, g)), 0.06, 0.06) + membro(T(x1, lerp(1.86, 1.72, g)), T(x2, lerp(1.5, 1.18, g)), 0.06, 0.055));
      }
    }
    J.T = T;
  }

  function cabeca(col, J, p, c, ap, t) {
    const g = J.gc, Q = quadroLocal(J.Hd, J.ah - 0);
    // a cabeça: quadro com y para cima girado pelo ângulo da cabeça
    const pts = mistPts(CAB_PERFIL, CAB_FRENTE, g).map((q) => Q(q[0], q[1]));
    col.add(CAM.CABECA, 'pele', fechado(pts));
    // orelha
    const ox = lerp(-0.07, -0.335, g);
    if (g < 0.9) col.add(CAM.CABECA, 'peleEscura', membro(Q(ox, 0.5), Q(ox - 0.01, 0.34), 0.07, 0.055));
    // cabelo
    const est = ap.cabelo;
    const capPts = (esc = 1) => mistPts(CAP_PERFIL, CAP_FRENTE, g).map((q) => Q(q[0] * esc, (q[1] - 0.5) * esc + 0.5));
    if (est === 'curto') col.add(CAM.CAB_FRENTE, 'cabelo', fechado(capPts(1)));
    else if (est === 'coque') {
      col.add(CAM.CAB_FRENTE, 'cabelo', fechado(capPts(0.985)));
      col.add(CAM.CAB_ATRAS, 'cabelo', circ(Q(lerp(-0.36, 0, g), lerp(0.95, 1.13, g)), 0.21));
    } else if (est === 'longo') {
      col.add(CAM.CAB_FRENTE, 'cabelo', fechado(capPts(1.02)));
      // a parte de baixo cai com a gravidade (não gira junto com a cabeça)
      col.add(CAM.CAB_ATRAS, 'cabelo', fechado(mistPts(LONGO_PERFIL, LONGO_FRENTE, g).map((q) => {
        const w = clamp((0.55 - q[1]) / 1.1);
        return w > 0 ? quadroLocal(J.Hd, J.ah * (1 - w * 0.85))(q[0], q[1]) : Q(q[0], q[1]);
      })));
    } else if (est === 'crespo') {
      col.add(CAM.CAB_FRENTE, 'cabelo', fechado(mistPts(FRANJA_CACHO_P, FRANJA_CACHO_F, g).map((q) => Q(q[0] * 1.08 + lerp(-0.1, 0, g), q[1] + 0.03))));
      col.add(CAM.CAB_ATRAS, 'cabelo', fechado(mistPts(CRESPO_PERFIL, CRESPO_FRENTE, g).map((q) => Q(q[0], q[1]))));
    } else if (est === 'cacheado') {
      col.add(CAM.CAB_FRENTE, 'cabelo', fechado(mistPts(FRANJA_CACHO_P, FRANJA_CACHO_F, g).map((q) => Q(q[0] + lerp(-0.1, 0, g), q[1]))));
      col.add(CAM.CAB_ATRAS, 'cabelo', fechado(mistPts(CACHO_PERFIL, CACHO_FRENTE, g).map((q) => Q(q[0], q[1]))));
    }
    // rosto (só nos estilos com detalhe)
    const olhos = clamp(p.olhos);
    const olho = (x, y) => {
      const ce = Q(x, y);
      if (olhos > 0.25) col.det(CAM.CABECA, 'olho', `M${f(ce[0] - 0.034)} ${f(ce[1])}a${f(0.034)} ${f(0.034 * olhos)} 0 1 0 ${f(0.068)} 0a${f(0.034)} ${f(0.034 * olhos)} 0 1 0 ${f(-0.068)} 0Z`);
      else col.det(CAM.CABECA, 'linha', aberta([Q(x - 0.045, y + 0.005), Q(x, y - 0.012), Q(x + 0.045, y + 0.005)]));
      col.det(CAM.CABECA, 'linha', aberta([Q(x - 0.06, y + 0.1), Q(x + 0.005, y + 0.125 - 0.02 * p.boca * 0), Q(x + 0.06, y + 0.105)]));
    };
    const ex = lerp(0.26, -0.14, g);
    olho(ex, 0.5);
    if (g > 0.45) olho(lerp(0.4, 0.14, g), 0.5);
    // boca
    const mx = lerp(0.33, 0, g), my = 0.2, bw = lerp(0.05, 0.085, g), cv = 0.035 * p.boca;
    col.det(CAM.CABECA, 'linha', aberta([Q(mx - bw, my + cv), Q(mx, my - cv * 0.5), Q(mx + bw * lerp(0.4, 1, g), my + cv)]));
    // nariz de frente
    if (g > 0.5) col.det(CAM.CABECA, 'linha', aberta([Q(lerp(0.35, 0.02, g), 0.42), Q(lerp(0.4, 0.05, g), 0.33), Q(lerp(0.33, -0.02, g), 0.31)]));
    // óculos
    if (ap.oculos) {
      const lente = (x, y, w) => { const a = Q(x - w, y + 0.06), b = Q(x + w, y + 0.06), cc = Q(x + w, y - 0.06), d = Q(x - w, y - 0.06); return fechado([[...a, 1], [...b, 1], [...cc, 1], [...d, 1]]); };
      const lx = lerp(0.32, -0.14, g);
      let s = lente(lx, 0.5, lerp(0.07, 0.1, g));
      if (g > 0.45) s += lente(lerp(0.42, 0.14, g), 0.5, 0.1);
      col.det(CAM.ACESS, 'oculos', s + aberta([Q(lx - lerp(0.07, 0.1, g), 0.52), Q(lerp(-0.12, -0.34, g), 0.55)]));
    }
    J.Q = Q;
  }

  // móveis e cenário ligados à pose (cadeira, mesa com caderno, livros e luminária; degraus)
  function moveis(col, J, p) {
    const P = J.P;
    if (p.cadeira > 0.02) {
      const k = clamp(p.cadeira), sy = P[1] + 0.24, x0 = P[0] - 0.62, x1 = P[0] + 0.78;
      const s = (x, y) => [x, lerp(0, y, k)];
      col.add(CAM.MOVEL, 'movel', fechado([[...s(x0, sy), 1], [...s(x1, sy), 1], [...s(x1, sy + 0.11), 1], [...s(x0, sy + 0.11), 1]]));
      col.add(CAM.MOVEL, 'movel', membro(s(x1 - 0.08, sy + 0.08), [x1 - 0.12, 0], 0.045, 0.04) + membro(s(x0 + 0.08, sy + 0.08), [x0 + 0.1, 0], 0.045, 0.04));
      col.add(CAM.MOVEL, 'movel', membro(s(x0 + 0.04, sy + 0.05), s(x0 - 0.12, sy - 1.95), 0.05, 0.05));
      col.add(CAM.MOVEL, 'movel', membro(s(x0 - 0.06, sy - 1.2), s(x0 - 0.13, sy - 1.9), 0.11, 0.11));
    }
    if (p.mesa > 0.02) {
      const k = clamp(p.mesa), ty = P[1] - 1.22, xa = P[0] + 1.05, xb = P[0] + 4.3;
      const s = (x, y) => [x, lerp(0, y, k)];
      col.add(CAM.MESA, 'movel', fechado([[...s(xa, ty), 1], [...s(xb, ty), 1], [...s(xb, ty + 0.13), 1], [...s(xa, ty + 0.13), 1]]));
      col.add(CAM.MESA, 'movel', membro(s(xb - 0.25, ty + 0.1), [xb - 0.3, 0], 0.06, 0.06));
      col.add(CAM.MOVEL, 'movelEscuro', membro(s(xa + 0.3, ty + 0.1), [xa + 0.3, 0], 0.06, 0.06));
      // caderno aberto, pilha de livros, luminária
      col.add(CAM.MESA, 'papel', fechado([[...s(xa + 0.42, ty - 0.035), 1], [...s(xa + 1.55, ty - 0.035), 1], [...s(xa + 1.6, ty + 0.002), 1], [...s(xa + 0.38, ty + 0.002), 1]]));
      col.add(CAM.MESA, 'livro', fechado([[...s(xa + 2.0, ty - 0.2), 1], [...s(xa + 2.85, ty - 0.2), 1], [...s(xa + 2.85, ty), 1], [...s(xa + 2.0, ty), 1]]));
      col.add(CAM.MESA, 'livro2', fechado([[...s(xa + 2.08, ty - 0.36), 1], [...s(xa + 2.75, ty - 0.36), 1], [...s(xa + 2.75, ty - 0.2), 1], [...s(xa + 2.08, ty - 0.2), 1]]));
      const lb = s(xa + 3.0, ty), l1 = s(xa + 2.6, ty - 1.45), l2 = s(xa + 1.75, ty - 1.25);
      col.add(CAM.MESA, 'objeto', fechado([[lb[0] - 0.22, lb[1], 1], [lb[0] + 0.22, lb[1], 1], [lb[0] + 0.15, lb[1] - 0.07], [lb[0] - 0.15, lb[1] - 0.07]]));
      col.add(CAM.MESA, 'objeto', membro([lb[0], lb[1] - 0.05], l1, 0.035, 0.035) + membro(l1, l2, 0.035, 0.035) + circ(l1, 0.06));
      const ab = baixo(angPara(l1, l2) + 35), hd = mais(l2, ab, 0.0);
      const ca = baixo(angPara(l1, l2) - 30);
      col.add(CAM.MESA, 'objeto', fechado([[...mais(hd, ca, -0.12), 1], [...mais(hd, ab, 0.32), 1], [...mais(mais(hd, ab, 0.32), ca, 0.26)], [...mais(hd, ca, 0.2), 1]]));
      col.luzes.push({ x: xa + 1.05, y: ty - 0.1, k: k * 0.8, mesa: true });
      J.mesa = { ty, xa, xb };
    }
    if (p.degraus > 0.02) {
      // degraus sob o pé da frente
      const e = J.pernas.P, fr = quadroPe(e.A, e.af);
      const sola = fr(0.3, 0.28), calc = fr(-0.18, 0.27);
      const h = clamp(-Math.max(sola[1], calc[1]), 0.15, 2), D = 1.25, x0 = calc[0] - 0.3;
      const k = clamp(p.degraus);
      const pts = [[x0, 0, 1]];
      for (let i = 1; i <= 4; i++) { pts.push([x0 + (i - 1) * D, -i * h * k, 1]); pts.push([x0 + i * D - (i === 4 ? -1.2 : 0), -i * h * k, 1]); }
      pts.push([x0 + 4 * D + 1.2, 0, 1]);
      col.add(CAM.MOVEL, 'movel', fechado(pts));
    }
  }

  // monta todas as partes de uma pose
  function partes(col, p, ap, t, olhar) {
    const c = ap.corpo;
    const J = rig(p, c, olhar);
    const g = clamp(p.giro);
    moveis(col, J, p);
    perna(col, CAM.PERNA_L, J.pernas.L, c, ap, g);
    perna(col, CAM.PERNA_P, J.pernas.P, c, ap, g);
    braco(col, CAM.BRACO_L, J.bracos.L, 'L', p, ap, c, 'pele');
    tronco(col, J, p, c, ap);
    cabeca(col, J, p, c, ap, t);
    braco(col, CAM.BRACO_P, J.bracos.P, 'P', p, ap, c, 'pele');
    return J;
  }

  // ------------------------------------------------------------------ estilos (renderizadores)
  let _uid = 0;
  const el = (tag, attrs, pai) => {
    const e = document.createElementNS(NS, tag);
    if (attrs) for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (pai) pai.appendChild(e);
    return e;
  };
  function defsDe(svg) {
    let d = svg.querySelector(':scope > defs');
    if (!d) d = el('defs', null, svg), svg.insertBefore(d, svg.firstChild);
    return d;
  }
  const svgDe = (g) => (g.ownerSVGElement || g);

  // Silhueta: corpo inteiro num path só (índigo profundo), luz de recorte numa borda vinda de rim.angulo.
  // rim: { angulo (de onde vem a luz, graus na tela: 0 = direita, -90 = de cima, 180 = esquerda), cor, largura (px), suave }
  function rSilhueta(g, cfg) {
    const id = ++_uid, svg = svgDe(g), defs = defsDe(svg);
    const rim = Object.assign({ angulo: -35, cor: '#ffb36b', largura: 7, suave: true }, cfg.rim || {});
    const corpo = cfg.corSilhueta || '#0b0920';
    const halo = cfg.halo ? el('ellipse', { fill: `url(#edinp-halo-${id})` }, g) : null;
    if (halo) {
      const rg = el('radialGradient', { id: `edinp-halo-${id}` }, defs);
      el('stop', { offset: '0', 'stop-color': rim.cor, 'stop-opacity': String(cfg.halo === true ? 0.5 : cfg.halo) }, rg);
      el('stop', { offset: '0.45', 'stop-color': rim.cor, 'stop-opacity': String((cfg.halo === true ? 0.5 : cfg.halo) * 0.35) }, rg);
      el('stop', { offset: '1', 'stop-color': rim.cor, 'stop-opacity': '0' }, rg);
    }
    const base = el('path', { fill: rim.cor }, g);
    let gClip = g, meioP = null;
    let fill = corpo;
    if (!cfg.simples) {
      const cp = el('clipPath', { id: `edinp-clip-${id}` }, defs);
      var clipP = el('path', null, cp);
      gClip = el('g', { 'clip-path': `url(#edinp-clip-${id})` }, g);
      // degradê sutil: um pouco mais claro do lado da luz
      const lg = el('linearGradient', { id: `edinp-grad-${id}`, x1: '0', y1: '0', x2: '1', y2: '1' }, defs);
      el('stop', { offset: '0', 'stop-color': cfg.corSilhuetaLuz || misturaCor(corpo, rim.cor, 0.12) }, lg);
      el('stop', { offset: '0.55', 'stop-color': corpo }, lg);
      el('stop', { offset: '1', 'stop-color': escurece(corpo, 0.4) }, lg);
      fill = `url(#edinp-grad-${id})`;
      var grad = lg;
      if (rim.suave) meioP = el('path', { fill: corpo, opacity: '0.55' }, gClip);
    }
    const escuro = el('path', { fill }, gClip);
    const telaP = el('path', { fill: '#dff1ff' }, g);
    const brilho = el('ellipse', { fill: `url(#edinp-tela-${id})`, opacity: '0' }, g);
    const rg2 = el('radialGradient', { id: `edinp-tela-${id}` }, defs);
    el('stop', { offset: '0', 'stop-color': '#bfe3ff', 'stop-opacity': '0.55' }, rg2);
    el('stop', { offset: '1', 'stop-color': '#bfe3ff', 'stop-opacity': '0' }, rg2);
    let ultDir = null;
    return {
      desenhar(col, esc, dir, J) {
        let d = '', tela = '';
        for (let i = 0; i < N_CAM; i++) {
          const s = col.s[i];
          for (const m in s) { if (m === 'tela' || m === 'luz') tela += s[m]; else d += s[m]; }
        }
        base.setAttribute('d', d);
        escuro.setAttribute('d', d);
        if (clipP) clipP.setAttribute('d', d);
        // deslocamento para longe da luz (no referencial local, que pode estar espelhado)
        const a = rim.angulo * RAD, w = rim.largura / esc;
        const lx = Math.cos(a) * dir, ly = Math.sin(a);
        escuro.setAttribute('transform', `translate(${(-lx * w).toFixed(2)} ${(-ly * w).toFixed(2)})`);
        if (meioP) { meioP.setAttribute('d', d); meioP.setAttribute('transform', `translate(${(-lx * w * 0.45).toFixed(2)} ${(-ly * w * 0.45).toFixed(2)})`); }
        if (grad && ultDir !== dir) {
          ultDir = dir;
          grad.setAttribute('x1', String(0.5 + 0.5 * lx)); grad.setAttribute('y1', String(0.5 + 0.5 * ly));
          grad.setAttribute('x2', String(0.5 - 0.5 * lx)); grad.setAttribute('y2', String(0.5 - 0.5 * ly));
        }
        telaP.setAttribute('d', tela);
        const lz = col.luzes.find((q) => !q.mesa);
        if (lz) {
          brilho.setAttribute('cx', f(lz.x - 0.1)); brilho.setAttribute('cy', f(lz.y - 0.5));
          brilho.setAttribute('rx', '90'); brilho.setAttribute('ry', '110'); brilho.setAttribute('opacity', (0.85 * lz.k).toFixed(3));
        } else { brilho.setAttribute('opacity', '0'); brilho.setAttribute('rx', '0'); brilho.setAttribute('ry', '0'); brilho.setAttribute('cx', '0'); brilho.setAttribute('cy', '0'); }
        if (halo && J) {
          halo.setAttribute('cx', f(J.N[0])); halo.setAttribute('cy', f(J.N[1] - 0.4));
          halo.setAttribute('rx', '310'); halo.setAttribute('ry', '380');
        }
      },
    };
  }

  // Ilustração: cores chapadas por material, membros de longe um pouco mais escuros, rosto em traço fino.
  function rIlustracao(g, cfg) {
    const ap = cfg.ap, nevoa = cfg.nevoa || 0, corNevoa = cfg.corNevoa || '#e9e6f5';
    const nv = (c) => (nevoa ? misturaCor(c, corNevoa, nevoa) : c);
    const pele = ap.pele, cab = ap.corCabelo;
    const cores = {
      pele, peleEscura: misturaCor(pele, '#5a2a1a', 0.16), cabelo: cab, roupa: ap.corRoupa, calca: ap.corCalca, sapato: ap.corSapato,
      sola: ap.corSapato === '#f4f1ea' ? '#d9d2c3' : '#f4f1ea', mochila: ap.corMochila, oculos: '#1d1830',
      movel: cfg.corMovel || '#b98a62', movelEscuro: escurece(cfg.corMovel || '#b98a62', 0.25), papel: '#fbf8f1', livro: '#e5484d', livro2: '#38a3d6',
      objeto: '#2b2a40', tela: '#cfe9ff', luz: 'rgba(255,214,150,0.0)',
    };
    const linha = cfg.corLinha || '#2a1b26';
    const chao = cfg.sombraChao !== false ? el('ellipse', { fill: 'rgba(20,10,40,0.16)' }, g) : null;
    const grupos = [];
    for (let i = 0; i < N_CAM; i++) {
      const gi = el('g', null, g), longe = i === CAM.BRACO_L || i === CAM.PERNA_L;
      const paths = {};
      for (const m of MATS[i]) {
        let c = cores[m];
        if (longe && m !== 'tela') c = escurece(c, 0.16);
        if (m === 'roupa' && i === CAM.BRACO_L) c = escurece(ap.corRoupa, 0.16);
        paths[m] = el('path', { fill: nv(c) }, gi);
      }
      const det = {
        linha: el('path', { fill: 'none', stroke: nv(i === CAM.TRONCO ? escurece(ap.corRoupa, 0.35) : linha), 'stroke-width': cfg.detalhe === false ? '0' : '3', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', opacity: i === CAM.TRONCO ? '0.55' : '0.9' }, gi),
        olho: el('path', { fill: nv(linha) }, gi),
        oculos: null,
      };
      if (i === CAM.ACESS) det.oculos = el('path', { fill: 'rgba(255,255,255,0.18)', stroke: nv('#1d1830'), 'stroke-width': '3.2', 'stroke-linejoin': 'round' }, gi);
      grupos.push({ paths, det });
    }
    return {
      desenhar(col, esc, dir, J) {
        for (let i = 0; i < N_CAM; i++) {
          const G = grupos[i], s = col.s[i], d = col.d[i];
          for (const m in G.paths) G.paths[m].setAttribute('d', s[m] || '');
          G.det.linha.setAttribute('d', cfg.detalhe === false ? '' : d.linha || '');
          G.det.olho.setAttribute('d', cfg.detalhe === false ? '' : d.olho || '');
          if (G.det.oculos) G.det.oculos.setAttribute('d', d.oculos || '');
        }
        if (chao && J) {
          const x = (J.pernas.P.A[0] + J.pernas.L.A[0]) / 2 + 0.25;
          chao.setAttribute('cx', f(x)); chao.setAttribute('cy', '0'); chao.setAttribute('rx', f(J.mesa ? 2.6 : 1.25)); chao.setAttribute('ry', '13');
        }
      },
    };
  }

  // Traço: linha contínua de caneta. Cada camada é uma união (contorno por fora, recheio cor de papel por cima),
  // a linha engrossa do lado da sombra (cópia deslocada) e um bloco de cor opcional sai fora de registro.
  function rTraco(g, cfg) {
    const papel = cfg.papel || '#f4efe6', tinta = cfg.tinta || '#1d1a33', lw = cfg.espessura || 4.2;
    const destaque = cfg.destaque === undefined ? '#F97316' : cfg.destaque;
    const a = ((cfg.rim && cfg.rim.angulo) != null ? cfg.rim.angulo : -35) * RAD;
    const grupos = [];
    const chao = el('path', { fill: 'none', stroke: tinta, 'stroke-width': String(lw * 0.8), 'stroke-linecap': 'round', opacity: '0.85' }, g);
    for (let i = 0; i < N_CAM; i++) {
      const gi = el('g', null, g);
      const st = el('path', { fill: 'none', stroke: tinta, 'stroke-width': String(lw * 2), 'stroke-linejoin': 'round' }, gi);
      const st2 = el('path', { fill: 'none', stroke: tinta, 'stroke-width': String(lw * 1.7), 'stroke-linejoin': 'round' }, gi);
      const fi = el('path', { fill: papel }, gi);
      const ln = el('path', { fill: 'none', stroke: tinta, 'stroke-width': String(lw * 0.75), 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, gi);
      const ol = el('path', { fill: tinta }, gi);
      grupos.push({ st, st2, fi, ln, ol });
    }
    const cor = destaque ? el('path', { fill: destaque, opacity: '0.85', style: 'mix-blend-mode:multiply' }, g) : null;
    let ult = null;
    return {
      desenhar(col, esc, dir, J) {
        const lx = Math.cos(a) * dir, ly = Math.sin(a), sh = lw * 0.75;
        const tr = `translate(${(-lx * sh).toFixed(2)} ${(-ly * sh).toFixed(2)})`;
        for (let i = 0; i < N_CAM; i++) {
          const G = grupos[i], s = col.s[i], d = col.d[i];
          let u = '';
          for (const m in s) if (m !== 'luz') u += s[m];
          G.st.setAttribute('d', u); G.st2.setAttribute('d', u); G.fi.setAttribute('d', u);
          if (ult !== tr) G.st2.setAttribute('transform', tr);
          G.ln.setAttribute('d', (d.linha || '') + (d.oculos || ''));
          G.ol.setAttribute('d', d.olho || '');
        }
        ult = tr;
        if (cor) cor.setAttribute('d', (col.s[CAM.TRONCO].roupa || '') + (col.s[CAM.BRACO_P].roupa || '') + (col.s[CAM.MESA].livro || ''));
        if (cor) cor.setAttribute('transform', `translate(${(9 * dir).toFixed(1)} 7)`);
        if (J) {
          const x = (J.pernas.P.A[0] + J.pernas.L.A[0]) / 2;
          chao.setAttribute('d', `M${f(x - 1.3)} 0L${f(x + 1.6 + (J.mesa ? 3 : 0))} 0`);
        }
      },
    };
  }

  function renderizador(g, estilo, cfg) {
    if (estilo === 'silhueta') return rSilhueta(g, cfg);
    if (estilo === 'traco') return rTraco(g, cfg);
    return rIlustracao(g, cfg);
  }

  // ------------------------------------------------------------------ pessoa
  // palco(el): <svg> que cobre o elemento, viewBox no tamanho do quadro (px de design)
  function palco(alvo, op = {}) {
    if (alvo instanceof SVGSVGElement) return alvo;
    const EV = window.EdinVideo;
    const W = op.w || (EV ? EV.w : alvo.clientWidth || 1080), H = op.h || (EV ? EV.h : alvo.clientHeight || 1920);
    const s = el('svg', { viewBox: `0 0 ${W} ${H}`, width: '100%', height: '100%', preserveAspectRatio: op.ajuste || 'xMidYMid slice' });
    s.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;overflow:visible';
    alvo.appendChild(s);
    return s;
  }

  // pessoa(alvo, op): op = { estilo, altura (px), x, y (px dos pés), dir, semente, aparência (pele, cabelo,
  // corCabelo, roupa, corRoupa, corCalca, corSapato, mochila, oculos, corpo), rim, halo, papel, tinta, destaque,
  // simples, nevoa, pose, fase, velocidade }
  function pessoa(alvo, op = {}) {
    const svg = alvo instanceof SVGElement ? alvo : palco(alvo, op);
    const sem = op.semente != null ? op.semente : 1;
    const ap = aparencia(sem, op);
    const estilo = op.estilo || 'ilustracao';
    const g = el('g', { class: 'edin-pessoa' }, svg);
    const r = renderizador(g, estilo, Object.assign({}, op, { ap }));
    const col = coletor();
    const P = {
      el: g, ap, estilo, semente: sem,
      x: op.x || 0, y: op.y || 0, altura: op.altura || 600, dir: op.dir || 1,
      poseAtual: op.pose || 'em-pe',
      J: null,
      // atualizar(t, { pose, x, y, altura, dir, olhar: [x, y] (px no mesmo svg) | null, vivo, opacidade })
      atualizar(t, o = {}) {
        if (o.x != null) P.x = o.x; if (o.y != null) P.y = o.y; if (o.altura != null) P.altura = o.altura; if (o.dir != null) P.dir = o.dir;
        const esc = (P.altura * (op.escalaFixa ? 1 : ap.escala)) / 750;
        let ps = o.pose != null ? o.pose : P.poseAtual;
        if (typeof ps === 'function') ps = ps(t);
        let q = typeof ps === 'string' ? pose(ps, t, { fase: op.fase || hash(sem, 3), velocidade: op.velocidade }) : pose0(ps);
        if (o.vivo !== false) q = vivo(q, t, sem, o.vivo != null ? o.vivo : 1);
        let olhar = null;
        if (o.olhar) {
          const ox = o.olhar[0] != null ? o.olhar[0] : o.olhar.x, oy = o.olhar[1] != null ? o.olhar[1] : o.olhar.y;
          olhar = { x: ((ox - P.x) / esc / 100) * P.dir, y: (oy - P.y) / esc / 100, peso: o.olhar.peso };
        }
        col.limpar();
        const J = partes(col, q, ap, t, olhar);
        P.J = J; P.pose = q;
        r.desenhar(col, esc, P.dir, J);
        g.setAttribute('transform', `translate(${P.x.toFixed(2)} ${P.y.toFixed(2)}) scale(${(esc * P.dir).toFixed(5)} ${esc.toFixed(5)})`);
        if (o.opacidade != null) g.setAttribute('opacity', o.opacidade.toFixed(3));
        P.col = col;
        return P;
      },
      // ponto do esqueleto em px do svg (ex.: P.ponto(P.J.bracos.P.Wr))
      ponto(q) {
        const esc = (P.altura * (op.escalaFixa ? 1 : ap.escala)) / 750;
        return [P.x + q[0] * 100 * esc * P.dir, P.y + q[1] * 100 * esc];
      },
    };
    return P;
  }

  // ------------------------------------------------------------------ multidão
  // multidao(el, { n, semente, estilo, profundidade: [kLonge, kPerto], faixas, horizonte, base, alturas: [longe, perto],
  //   poses, sobra, rim, nevoa, corNevoa, onda: { pose, inicio, duracao, espalhamento } })
  function multidao(alvo, op = {}) {
    const EV = window.EdinVideo;
    const W = op.w || (EV ? EV.w : 1080), H = op.h || (EV ? EV.h : 1920);
    const n = op.n || 40, sem = op.semente || 1, estilo = op.estilo || 'silhueta';
    const nf = op.faixas || 4;
    const [kL, kP] = op.profundidade || [0.55, 1.25];
    const hz = op.horizonte != null ? op.horizonte : 0.62, base = op.base != null ? op.base : 0.97;
    const [aL, aP] = op.alturas || [H * 0.13, H * 0.42];
    const poses = op.poses || ['andando', 'andando', 'andando', 'em-pe', 'olhando-celular', 'andando', 'cabeca-baixa', 'correndo', 'andando', 'em-pe'];
    const sobra = op.sobra != null ? op.sobra : 0.3;
    const r = aleatorio(sem * 17 + 3);
    const camadas = [];
    for (let i = 0; i < nf; i++) {
      const kk = nf === 1 ? kP : lerp(kL, kP, i / (nf - 1));
      const div = document.createElement('div');
      div.setAttribute('data-z', kk.toFixed(3));
      div.setAttribute('data-cobre', '0');
      div.setAttribute('data-decorativo', '');
      if (op.desfoque) { const df = op.desfoque[i]; if (df) div.setAttribute('data-desfoque', String(df)); }
      div.style.cssText = 'position:absolute;inset:0';
      alvo.appendChild(div);
      const svg = palco(div, { w: W, h: H });
      camadas.push({ div, svg, k: kk, pessoas: [] });
    }
    const pessoas = [];
    for (let i = 0; i < n; i++) {
      const d = Math.pow(r(), 0.8); // 0 = longe, 1 = perto
      const fx = Math.min(nf - 1, Math.floor(d * nf));
      const pz = op.poses && op.poses.length === 1 ? op.poses[0] : poses[Math.floor(r() * poses.length)];
      const anda = pz === 'andando' || pz === 'correndo';
      const dir = r() < 0.5 ? -1 : 1;
      const yb = lerp(hz * H, base * H, d);
      const alt = lerp(aL, aP, d * d);
      const x0 = lerp(-sobra, 1 + sobra, r()) * W;
      const s = 900 + i * 13 + sem * 101;
      pessoas.push({ d, fx, pz, anda, dir, yb, alt, x0, sem: s, fase: r(), vel: 0.85 + r() * 0.3, atraso: r() });
    }
    pessoas.sort((a, b) => a.d - b.d);
    for (const p of pessoas) {
      const c = camadas[p.fx];
      const nev = op.nevoa != null ? op.nevoa * (1 - p.d) : 0;
      const corSil = op.corSilhueta ? misturaCor(op.corSilhueta, op.corNevoa || '#3a2f6b', (op.nevoaSilhueta != null ? op.nevoaSilhueta : 0.55) * (1 - p.d)) : misturaCor('#0b0920', op.corNevoa || '#3a2f6b', (op.nevoaSilhueta != null ? op.nevoaSilhueta : 0.55) * (1 - p.d));
      p.obj = pessoa(c.svg, Object.assign({}, op.aparencia || {}, {
        estilo, semente: p.sem, altura: p.alt, x: p.x0, y: p.yb, dir: p.dir, simples: true,
        rim: Object.assign({}, op.rim || {}, { largura: ((op.rim && op.rim.largura) || 6) * lerp(0.45, 1, p.d), suave: false }),
        corSilhueta: corSil, nevoa: nev, corNevoa: op.corNevoa, detalhe: p.d > 0.45, sombraChao: p.d > 0.3,
        papel: op.papel, tinta: op.tinta, destaque: op.destaque === undefined ? null : op.destaque, espessura: op.espessura ? op.espessura / lerp(0.35, 1, p.d) : 4.5 / lerp(0.4, 1, p.d),
        fase: p.fase, velocidade: p.vel,
      }));
      c.pessoas.push(p);
    }
    const largura = W * (1 + 2 * sobra);
    const onda = op.onda || null;
    // integral de (1 - suave) para frear quem anda quando a onda chega
    const G = (u) => (u <= 0 ? u : u >= 1 ? 0.5 + (u - 1) * 0 : u - (u ** 6 - 3 * u ** 5 + 2.5 * u ** 4));
    return {
      camadas: camadas.map((c) => c.div), pessoas,
      atualizar(t) {
        for (const p of pessoas) {
          let k = 0, tm = t;
          if (onda) {
            const t0 = onda.inicio + (onda.espalhamento || 1) * (onda.ordem === 'aleatoria' ? p.atraso : clamp((p.x0 / W + sobra) / (1 + 2 * sobra)));
            const du = onda.duracao || 0.7;
            k = clamp((t - t0) / du);
            if (t > t0) tm = t0 + du * G((t - t0) / du);
          }
          let base = p.pz;
          let q = typeof base === 'string' ? pose(base, tm, { fase: p.fase, velocidade: p.vel }) : base;
          let x = p.x0;
          if (p.anda) {
            const av = (q.avanco || 0) * (p.alt * p.obj.ap.escala / 750) * 100;
            x = p.x0 + p.dir * av;
            x = ((((x + sobra * W) % largura) + largura) % largura) - sobra * W;
          }
          if (k > 0) q = mistura(q, pose(onda.pose, t), k);
          p.obj.atualizar(t, { pose: q, x });
        }
      },
    };
  }

  // ------------------------------------------------------------------ closes de detalhe
  // detalhe(el, tipo, op): planos detalhe em escala grande com o mesmo rig.
  //   tipo: 'mao-escrevendo' | 'mao-celular' | 'punho' | 'perfil' | 'pes-andando'
  //   op: { estilo, semente, zoom, rim, halo, papel, ... (aparência) }
  function detalhe(alvo, tipo, op = {}) {
    const EV = window.EdinVideo;
    const W = op.w || (EV ? EV.w : alvo.clientWidth || 1080), H = op.h || (EV ? EV.h : alvo.clientHeight || 1920);
    const svg = op.svg || palco(alvo, { w: W, h: H, ajuste: 'xMidYMid slice' });
    const conf = {
      'mao-escrevendo': { pose: 'sentado-estudando', foco: (J) => mais(J.bracos.P.Wr, [0.05, -0.1]), cab: 1.6, ajuste: { mesa: 0, cadeira: 0, sentidoEscrita: -1 }, dir: -1 },
      'mao-celular': { pose: 'olhando-celular', foco: (J) => mais(J.bracos.P.Wr, [0.18, -0.2]), cab: 2.0, ajuste: { giro: 0.7 } },
      'punho': { pose: 'punho-erguido', foco: (J) => mais(J.bracos.P.Wr, baixo(J.bracos.P.aM), 0.12), cab: 1.7 },
      'perfil': { pose: 'olhando-horizonte', foco: (J) => mais(J.Hd, [0.08, -0.4]), cab: 1.75, ajuste: { ikP: 0, mAbsP: 0, oP: 2, cP: 10, giro: 0, cabeca: -8 } },
      'pes-andando': { pose: 'andando', foco: (J) => [J.P[0] + 0.35, -1.0], cab: 3.6 },
    }[tipo];
    if (!conf) throw new Error(`[edin-pessoas] detalhe desconhecido "${tipo}"`);
    const zoom = op.zoom || 1;
    // quantas cabeças de largura cabem no quadro
    const vis = conf.cab / zoom;
    const esc = Math.min(W, H) / (vis * 100);
    const altura = esc * 750;
    const dir = op.dir || conf.dir || 1;
    const p = pessoa(svg, Object.assign({ escalaFixa: true, halo: false }, op, { altura, x: 0, y: 0, dir }));
    const ajuste = conf.ajuste || null;
    const poseDe = (t) => {
      let q = pose(conf.pose, t, { fase: 0.1 });
      if (ajuste) Object.assign(q, ajuste);
      if (op.ajuste) Object.assign(q, op.ajuste);
      return q;
    };
    // enquadramento fixo (calculado em t = 0): o plano não persegue a mão
    const q0 = vivo(poseDe(0), 0, p.semente, 0);
    const J0 = rig(q0, p.ap.corpo, null);
    const foco = conf.foco(J0);
    const ox = W * (op.cx != null ? op.cx : 0.5) - foco[0] * 100 * esc * dir, oy = H * (op.cy != null ? op.cy : 0.5) - foco[1] * 100 * esc;
    // escrita: o rastro da ponta da caneta no papel
    // o papel é um plano de frente para a câmera (visto de cima), atrás da mão; a escrita é o rastro da ponta da caneta
    let rastro = null;
    if (tipo === 'mao-escrevendo') {
      const sil = op.estilo === 'silhueta';
      const fol = el('g', null, null);
      p.el.insertBefore(fol, p.el.firstChild);
      const yp = J0.bracos.P.Wr[1] - 0.5;
      const x0 = J0.bracos.P.Wr[0] - 2.2;
      el('rect', { x: f(x0), y: f(yp), width: f(5), height: f(4), rx: '4', fill: sil ? '#1a1440' : op.estilo === 'traco' ? '#fbf8f1' : '#fbf8f1',
        stroke: op.estilo === 'traco' ? '#1d1a33' : 'none', 'stroke-width': '2', transform: `rotate(-4 ${f(x0)} ${f(yp)})` }, fol);
      let pauta = '';
      for (let i = 1; i < 12; i++) pauta += `M${f(x0)} ${f(yp + i * 0.24 + 0.02)}L${f(x0 + 5)} ${f(yp + i * 0.24 + 0.02)}`;
      el('path', { d: pauta, stroke: sil ? 'rgba(255,194,122,.18)' : 'rgba(79,70,229,.22)', 'stroke-width': '1.5', fill: 'none', transform: `rotate(-4 ${f(x0)} ${f(yp)})` }, fol);
      rastro = el('path', { fill: 'none', stroke: sil ? (op.rim && op.rim.cor) || '#ffb36b' : '#2b2a6a', 'stroke-width': '2.6', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, fol);
    }
    const tela = tipo === 'mao-celular' ? el('g', null, p.el) : null;
    let telaLinhas = null;
    if (tela) telaLinhas = el('path', { fill: 'none', stroke: op.estilo === 'traco' ? '#1d1a33' : '#7fb6e6', 'stroke-width': '2.4', 'stroke-linecap': 'round' }, tela);
    let chao = null;
    if (tipo === 'pes-andando') {
      chao = el('path', { fill: 'none', stroke: op.estilo === 'silhueta' ? (op.rim && op.rim.cor) || '#ffb36b' : '#2b2a40', 'stroke-width': '3', 'stroke-dasharray': '30 26', opacity: '0.6' }, null);
      p.el.insertBefore(chao, p.el.firstChild);
    }
    return {
      pessoa: p, svg,
      atualizar(t) {
        p.atualizar(t, { pose: poseDe(t), x: ox, y: oy });
        if (rastro) {
          // amostra a ponta da caneta desde o início da linha atual
          const T = 3.2, t0 = Math.floor(t / T) * T;
          const pts = [];
          for (let s = t0; s <= t + 1e-6; s += 1 / 90) {
            const q = vivo(poseDe(s), s, p.semente);
            const J = rig(q, p.ap.corpo, null);
            pts.push(caneta(J.bracos.P, q.ladoP, 1.14 * p.ap.corpo.gr)[1]);
          }
          let d = '';
          if (pts.length > 1) {
            d = `M${f(pts[0][0])} ${f(pts[0][1])}`;
            for (let i = 1; i < pts.length; i++) d += `L${f(pts[i][0])} ${f(pts[i][1])}`;
          }
          rastro.setAttribute('d', d);
        }
        if (telaLinhas && p.col.celular) {
          // conteúdo da tela rolando (o polegar rola o feed)
          const C = p.col.celular, F = C.F, rol = (t * 0.22) % 0.13, iw = C.lw / 2 - 0.06;
          let d = '';
          for (let i = 0; i < 7; i++) {
            const y = -0.22 + i * 0.13 - rol;
            if (y < -0.24 || y > 0.33 || iw < 0.04) continue;
            const w = i % 3 === 1 ? 0.55 : 1;
            d += aberta([F(C.cx - iw, C.cy + y), F(C.cx - iw + 2 * iw * w, C.cy + y)]);
          }
          telaLinhas.setAttribute('d', d);
        }
        if (chao) {
          const off = ((t * 0.95 * AVANCO.andando * 100) % 56);
          chao.setAttribute('d', `M${-800 - off} 0L${800 - off} 0`);
        }
      },
    };
  }

  // ------------------------------------------------------------------ calibração dos ciclos
  // distância por volta: o pé de apoio (o mais baixo) anda para trás em relação ao quadril; o corpo anda o mesmo
  (function calibrar() {
    const c = corpoPadrao('a');
    for (const nome of ['andando', 'correndo']) {
      const N = 240;
      let soma = 0, ant = null;
      for (let i = 0; i <= N; i++) {
        const q = ciclo(nome, i / N / CAD[nome]);
        const J = rig(q, c, null);
        const pp = J.pernas.P.A[0] - J.P[0], pl = J.pernas.L.A[0] - J.P[0];
        const apoio = J.pernas.P.A[1] > J.pernas.L.A[1] ? 'P' : 'L';
        const x = apoio === 'P' ? pp : pl;
        if (ant && ant.apoio === apoio) soma += Math.max(0, ant.x - x);
        ant = { apoio, x };
      }
      AVANCO[nome] = soma;
    }
  })();

  window.EdinPessoas = {
    pessoa, multidao, detalhe, palco, pose, poses: POSES, nomes: Object.keys(POSES).concat(['andando', 'correndo', 'comemorando']),
    mistura, ciclo, vivo, piscar, aparencia, rig, avanco: AVANCO,
    cores: { peles: PELES, cabelos: CABELOS, roupas: ROUPAS, calcas: CALCAS, sapatos: SAPATOS },
    penteados: ['curto', 'crespo', 'cacheado', 'longo', 'coque', 'careca'], roupasTipo: ['camiseta', 'moletom', 'camisa'],
  };
})();
