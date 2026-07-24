// Lienzo del recorrido.
//
// Todo lo que se dibuja aquí viene de un evento real del backend: un nodo solo
// se enciende cuando esa etapa está corriendo, los paquetes que viajan por una
// conexión son los fragmentos que de verdad pasaron por ahí, y cada punto del
// índice es un fragmento indexado.

const NS = 'http://www.w3.org/2000/svg';

const SPINE_Y = 420;
const SPINE_H = 80;
const SPINE_MID = SPINE_Y + SPINE_H / 2;

const INDICE = { x: 350, y: 200, w: 260, h: 120 };

const STAGES = {
  consulta: { x: 20, y: SPINE_Y, w: 165, h: SPINE_H, kicker: 'entrada', title: 'Consulta', sub: 'tu pregunta' },
  indice: { ...INDICE, kicker: 'faiss', title: 'Índice vectorial', sub: 'sin construir', detail: false },
  recuperacion: { x: 250, y: SPINE_Y, w: 190, h: SPINE_H, kicker: 'búsqueda', title: 'Recuperación', sub: 'similitud coseno' },
  modelo: { x: 505, y: SPINE_Y, w: 180, h: SPINE_H, kicker: 'generación', title: 'Modelo', sub: '—' },
  respuesta: { x: 760, y: SPINE_Y, w: 155, h: SPINE_H, kicker: 'salida', title: 'Respuesta', sub: 'con citas' },
};

const DOC = { w: 150, h: 72, y: 24, gap: 22, max: 4 };

// Rejilla de fragmentos dentro del nodo del índice.
const REJILLA = { x: INDICE.x + 16, y: INDICE.y + 64, w: INDICE.w - 32, h: INDICE.h - 76 };
const CELDA_MAX = 13;
const CELDA_MIN = 3;

/** Reparte n fragmentos en la caja del índice conservando su proporción. */
function medirRejilla(n) {
  const aspecto = REJILLA.w / REJILLA.h;
  let cols = Math.max(1, Math.ceil(Math.sqrt(n * aspecto)));
  let celda = Math.min(REJILLA.w / cols, REJILLA.h / Math.ceil(n / cols), CELDA_MAX);

  if (celda < CELDA_MIN) {
    celda = CELDA_MIN;
    cols = Math.floor(REJILLA.w / celda);
  }

  const filas = Math.max(1, Math.floor(REJILLA.h / celda));
  return { cols, celda, cabe: Math.min(n, cols * filas) };
}

// Qué conexiones se encienden cuando una etapa cambia de estado.
const WIRING = {
  consulta: { done: [['consulta-recuperacion', 'done']] },
  recuperacion: {
    active: [['consulta-recuperacion', 'active'], ['indice-recuperacion', 'active']],
    done: [['consulta-recuperacion', 'done'], ['indice-recuperacion', 'done']],
  },
  modelo: { active: [['recuperacion-modelo', 'active']], done: [['recuperacion-modelo', 'done']] },
  respuesta: { done: [['modelo-respuesta', 'done']] },
};

const sinMovimiento = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const el = (tag, attrs = {}) => {
  const nodo = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) nodo.setAttribute(k, v);
  return nodo;
};

const text = (x, y, cls, contenido) => {
  const nodo = el('text', { x, y, class: cls });
  nodo.textContent = contenido;
  return nodo;
};

const truncar = (valor, largo) => (valor.length > largo ? `${valor.slice(0, largo - 1)}…` : valor);
const idSeguro = (valor) => valor.replace(/[^a-zA-Z0-9_-]/g, '-');

const curva = (x1, y1, x2, y2, vertical) =>
  vertical
    ? `M ${x1} ${y1} C ${x1} ${y1 + 46}, ${x2} ${y2 - 46}, ${x2} ${y2}`
    : `M ${x1} ${y1} C ${x1 + 52} ${y1}, ${x2 - 52} ${y2}, ${x2} ${y2}`;

export class Flow {
  constructor(svg, { onDocumentClick, onDocumentHover } = {}) {
    this.svg = svg;
    this.onDocumentClick = onDocumentClick;
    this.onDocumentHover = onDocumentHover;
    this.documents = [];
    this.edges = new Map();
    this.nodes = new Map();
    this.dots = new Map(); // chunk_id -> punto de la rejilla
    this.packets = new Map();
    this.primerDibujo = true;
    this.render();
  }

  // ---------------------------------------------------------------- dibujo

  render() {
    this.svg.replaceChildren();
    this.edges.clear();
    this.nodes.clear();
    this.dots.clear();
    this.packets.clear();

    this.layerEdges = el('g');
    this.layerPackets = el('g');
    this.layerNodes = el('g');
    this.svg.append(this.layerEdges, this.layerPackets, this.layerNodes);

    const visibles = this.documents.slice(0, DOC.max);
    const extra = this.documents.length - visibles.length;
    const total = visibles.length + (extra > 0 ? 1 : 0);

    const anchoFila = total * DOC.w + Math.max(0, total - 1) * DOC.gap;
    const inicio = 480 - anchoFila / 2;

    visibles.forEach((doc, i) => {
      const x = inicio + i * (DOC.w + DOC.gap);
      this.drawDocument(doc, x, i);
      this.drawEdge(`doc:${doc.id}`, x + DOC.w / 2, DOC.y + DOC.h, 480, INDICE.y, true);
    });

    if (extra > 0) {
      const x = inicio + visibles.length * (DOC.w + DOC.gap);
      const grupo = this.drawNode('mas-docs', {
        ...DOC,
        x,
        kicker: 'biblioteca',
        title: `+${extra} más`,
        sub: 'abrir biblioteca',
      });
      grupo.classList.add('node-doc');
      grupo.addEventListener('click', () => this.onDocumentClick?.(null));
      this.drawEdge('doc:mas', x + DOC.w / 2, DOC.y + DOC.h, 480, INDICE.y, true);
    }

    if (!this.documents.length) {
      const aviso = text(480, DOC.y + 40, 'node-sub', 'La biblioteca está vacía');
      aviso.setAttribute('text-anchor', 'middle');
      this.layerNodes.append(aviso);
    }

    for (const [id, cfg] of Object.entries(STAGES)) this.drawNode(id, cfg);
    this.drawGrid();

    const { consulta, recuperacion, modelo, respuesta } = STAGES;
    this.drawEdge('indice-recuperacion', 480, INDICE.y + INDICE.h, recuperacion.x + 95, recuperacion.y, true);
    this.drawEdge('consulta-recuperacion', consulta.x + consulta.w, SPINE_MID, recuperacion.x, SPINE_MID, false);
    this.drawEdge('recuperacion-modelo', recuperacion.x + recuperacion.w, SPINE_MID, modelo.x, SPINE_MID, false);
    this.drawEdge('modelo-respuesta', modelo.x + modelo.w, SPINE_MID, respuesta.x, SPINE_MID, false);

    if (this.primerDibujo) {
      this.animateDrawIn();
      this.primerDibujo = false;
    }
  }

  drawNode(id, cfg) {
    const { x, y, w, h, kicker, title, sub, detail = true } = cfg;
    const group = el('g', { class: 'node', 'data-id': id, 'data-state': 'idle' });

    const caja = el('rect', { class: 'node-box', x, y, width: w, height: h, rx: 2 });
    group.append(
      caja,
      el('rect', { class: 'node-tab', x, y, width: 4, height: h }),
      text(x + 15, y + 18, 'node-kicker', kicker.toUpperCase()),
      text(x + 15, y + 37, 'node-title', title),
    );

    const subtitulo = text(x + 15, y + 54, 'node-sub', sub);
    group.append(subtitulo);

    // la medición de la etapa solo cabe en los nodos altos del eje
    const detalle = text(x + 15, y + 70, 'node-sub', '');
    if (detail && h >= SPINE_H) group.append(detalle);

    group.append(el('path', { class: 'node-tick', d: `M ${x + w - 22} ${y + 15} l 4 4 l 7 -8` }));

    this.layerNodes.append(group);
    this.nodes.set(id, { group, caja, subtitulo, detalle, cfg });
    return group;
  }

  drawDocument(doc, x, orden) {
    const group = this.drawNode(`doc:${doc.id}`, {
      x,
      y: DOC.y,
      w: DOC.w,
      h: DOC.h,
      kicker: doc.kind,
      title: truncar(doc.filename, 17),
      sub: `${doc.chunks} fragmentos`,
    });

    group.classList.add('node-doc');
    group.dataset.band = orden % 2 === 0 ? 'a' : 'b';
    group.addEventListener('click', () => this.onDocumentClick?.(doc.id));
    group.addEventListener('mouseenter', () => this.onDocumentHover?.(doc.id, true));
    group.addEventListener('mouseleave', () => this.onDocumentHover?.(doc.id, false));

    const track = el('rect', { class: 'node-relev-track', x: x + 15, y: DOC.y + 60, width: DOC.w - 62, height: 4, rx: 1 });
    const fill = el('rect', { class: 'node-relev-fill', x: x + 15, y: DOC.y + 60, width: 0, height: 4, rx: 1 });
    const label = text(x + DOC.w - 40, DOC.y + 65, 'node-relev-label', '');

    track.setAttribute('opacity', '0');
    group.append(track, fill, label);
    Object.assign(this.nodes.get(`doc:${doc.id}`), { track, fill, label });
  }

  /**
   * Rejilla de fragmentos: un punto por fragmento indexado, en el orden en que
   * viven en el índice. Las bandas alternas separan un documento del siguiente.
   */
  drawGrid() {
    const grupo = el('g', { class: 'grid-chunks' });
    this.layerNodes.append(grupo);

    const totales = this.documents.reduce((suma, doc) => suma + doc.chunks, 0);
    if (!totales) return;

    // La celda se estira o se aprieta para que la rejilla llene el nodo:
    // cinco fragmentos se ven como bloques, dos mil como una trama.
    const { cols, celda, cabe } = medirRejilla(totales);

    // centrada en su caja, para que una biblioteca pequeña no se vea perdida
    const usadas = Math.min(cols, cabe);
    const filasUsadas = Math.ceil(cabe / cols);
    const origenX = REJILLA.x + (REJILLA.w - usadas * celda) / 2;
    const origenY = REJILLA.y + (REJILLA.h - filasUsadas * celda) / 2;

    let posicion = 0;
    for (const doc of this.documents) {
      for (let i = 0; i < doc.chunks; i++) {
        if (posicion >= cabe) break;
        const punto = el('rect', {
          class: 'chunk-dot',
          'data-doc': doc.id,
          x: origenX + (posicion % cols) * celda,
          y: origenY + Math.floor(posicion / cols) * celda,
          width: Math.max(2, celda - 2.5),
          height: Math.max(2, celda - 2.5),
          rx: 0.5,
        });
        grupo.append(punto);
        this.dots.set(`${doc.id}:${i}`, punto);
        posicion += 1;
      }
    }

    if (totales > cabe) {
      const nota = text(REJILLA.x + REJILLA.w, REJILLA.y - 5, 'node-relev-label', `muestra ${cabe} de ${totales}`);
      nota.setAttribute('text-anchor', 'end');
      grupo.append(nota);
    }
  }

  drawEdge(id, x1, y1, x2, y2, vertical) {
    const path = el('path', {
      id: `edge-${idSeguro(id)}`,
      class: 'edge',
      'data-state': 'idle',
      d: curva(x1, y1, x2, y2, vertical),
    });
    this.layerEdges.append(path);
    this.edges.set(id, path);
  }

  animateDrawIn() {
    if (sinMovimiento()) return;

    this.svg.querySelectorAll('.node').forEach((nodo, i) => {
      nodo.style.setProperty('--retraso', `${i * 55}ms`);
      nodo.classList.add('node-draw');
    });

    let i = 0;
    for (const path of this.edges.values()) {
      path.style.setProperty('--len', path.getTotalLength());
      path.style.setProperty('--retraso', `${180 + i * 45}ms`);
      path.classList.add('flow-draw');
      i += 1;
    }
  }

  // --------------------------------------------------------------- paquetes

  /** Cuadraditos que recorren una conexión mientras esa etapa trabaja. */
  spawnPackets(edgeId, cantidad = 3, tono = 'plot') {
    if (sinMovimiento() || this.packets.has(edgeId)) return;
    const path = this.edges.get(edgeId);
    if (!path) return;

    const grupo = el('g', { class: 'packets' });
    const duracion = 1.1;

    for (let i = 0; i < Math.min(cantidad, 6); i++) {
      const paquete = el('rect', { class: `packet packet-${tono}`, x: -3, y: -3, width: 6, height: 6, rx: 1 });
      const motion = el('animateMotion', {
        dur: `${duracion}s`,
        repeatCount: 'indefinite',
        begin: `-${(i * duracion) / Math.min(cantidad, 6)}s`,
        rotate: 'auto',
      });
      motion.append(el('mpath', { href: `#edge-${idSeguro(edgeId)}` }));
      paquete.append(motion);
      grupo.append(paquete);
    }

    this.layerPackets.append(grupo);
    this.packets.set(edgeId, grupo);
  }

  clearPackets(edgeId) {
    if (edgeId === undefined) {
      for (const grupo of this.packets.values()) grupo.remove();
      this.packets.clear();
      return;
    }
    this.packets.get(edgeId)?.remove();
    this.packets.delete(edgeId);
  }

  // ---------------------------------------------------------------- estado

  setDocuments(documentos) {
    this.documents = documentos;
    this.render();
  }

  setIndex({ status, chunks, documents }) {
    const nodo = this.nodes.get('indice');
    if (!nodo) return;
    const leyenda = {
      listo: `${chunks} fragmentos · ${documents} doc.`,
      indexando: 'construyendo…',
      vacio: 'sin documentos',
      error: 'no se pudo construir',
    };
    nodo.subtitulo.textContent = leyenda[status] ?? status;
    nodo.group.dataset.state = status === 'listo' ? 'done' : status === 'indexando' ? 'active' : 'idle';
  }

  setModel(nombre) {
    const nodo = this.nodes.get('modelo');
    if (nodo) nodo.subtitulo.textContent = truncar(nombre, 22);
  }

  setStage(id, status, meta = {}) {
    const nodo = this.nodes.get(id);
    if (nodo) {
      nodo.group.dataset.state = status;
      if (meta.ms != null && nodo.detalle) nodo.detalle.textContent = formatoMs(meta.ms);
      if (id === 'recuperacion' && meta.k) nodo.subtitulo.textContent = `k=${meta.k} de ${meta.chunks}`;
      if (id === 'consulta' && meta.dims) nodo.subtitulo.textContent = `vector de ${meta.dims}`;
      // la salida no tarda: lo que importa es su tamaño
      if (id === 'respuesta' && meta.chars != null && nodo.detalle) {
        nodo.detalle.textContent = `${meta.chars} caracteres`;
      }
    }

    for (const [edgeId, estado] of WIRING[id]?.[status] ?? []) {
      const edge = this.edges.get(edgeId);
      if (!edge) continue;
      edge.dataset.state = estado;
      if (estado === 'active') this.spawnPackets(edgeId, 3);
      else this.clearPackets(edgeId);
    }
  }

  /** Marca qué documentos aportaron fragmentos y con qué relevancia. */
  setContributions(contribuciones) {
    for (const doc of this.documents) {
      const nodo = this.nodes.get(`doc:${doc.id}`);
      const aporte = contribuciones.find((c) => c.doc_id === doc.id);
      const edge = this.edges.get(`doc:${doc.id}`);

      if (!nodo) continue;
      nodo.group.dataset.consulted = aporte ? 'true' : 'false';
      nodo.track?.setAttribute('opacity', aporte ? '1' : '0');
      nodo.fill?.setAttribute('width', aporte ? (DOC.w - 62) * aporte.score : 0);
      if (nodo.label) nodo.label.textContent = aporte ? `${Math.round(aporte.score * 100)}%` : '';
      if (nodo.subtitulo) {
        nodo.subtitulo.textContent = aporte
          ? `${aporte.count} de ${doc.chunks} usados`
          : `${doc.chunks} fragmentos`;
      }
      if (edge) edge.dataset.carried = aporte ? 'true' : 'false';
    }
  }

  /** Los fragmentos recuperados salen de su documento hacia el índice. */
  pulseDocuments(contribuciones) {
    for (const aporte of contribuciones) {
      const edgeId = `doc:${aporte.doc_id}`;
      if (!this.edges.has(edgeId)) continue;
      this.spawnPackets(edgeId, aporte.count, 'marker');
      setTimeout(() => this.clearPackets(edgeId), 1600);
    }
  }

  /** Enciende en la rejilla los fragmentos que se recuperaron. */
  setHits(hits) {
    for (const punto of this.dots.values()) punto.removeAttribute('data-hit');
    for (const hit of hits) this.dots.get(hit.chunk_id)?.setAttribute('data-hit', 'true');
  }

  /** Resalta un documento: su nodo y su región del índice. */
  highlightDocument(docId, activo) {
    const nodo = this.nodes.get(`doc:${docId}`);
    if (nodo) nodo.group.dataset.hover = activo ? 'true' : 'false';
    for (const punto of this.dots.values()) {
      if (punto.getAttribute('data-doc') === docId) {
        punto.toggleAttribute('data-focus', activo);
      }
    }
  }

  reset() {
    this.clearPackets();
    for (const [id, nodo] of this.nodes) {
      if (id.startsWith('doc:') || id === 'indice' || id === 'mas-docs') continue;
      nodo.group.dataset.state = 'idle';
      if (nodo.detalle) nodo.detalle.textContent = '';
    }
    for (const [id, edge] of this.edges) {
      if (id.startsWith('doc:')) continue;
      edge.dataset.state = 'idle';
    }
    for (const punto of this.dots.values()) punto.removeAttribute('data-hit');
  }
}

export const formatoMs = (ms) => {
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)} s`;
  return ms < 1 ? '<1 ms' : `${Math.round(ms)} ms`;
};
