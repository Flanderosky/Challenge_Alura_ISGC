// Lienzo del recorrido.
//
// Todo lo que se dibuja aquí viene de un evento real del backend: un nodo solo
// se enciende cuando esa etapa está corriendo, y las bandas amarillas de los
// documentos son la relevancia que devolvió la búsqueda.

const NS = 'http://www.w3.org/2000/svg';
const SPINE_Y = 420;
const SPINE_H = 80;
const SPINE_MID = SPINE_Y + SPINE_H / 2;

const STAGES = {
  consulta: { x: 20, y: SPINE_Y, w: 165, h: SPINE_H, kicker: 'entrada', title: 'Consulta', sub: 'tu pregunta' },
  indice: { x: 385, y: 215, w: 190, h: SPINE_H, kicker: 'faiss', title: 'Índice vectorial', sub: 'sin construir' },
  recuperacion: { x: 250, y: SPINE_Y, w: 190, h: SPINE_H, kicker: 'búsqueda', title: 'Recuperación', sub: 'similitud coseno' },
  modelo: { x: 505, y: SPINE_Y, w: 180, h: SPINE_H, kicker: 'generación', title: 'Modelo', sub: '—' },
  respuesta: { x: 760, y: SPINE_Y, w: 155, h: SPINE_H, kicker: 'salida', title: 'Respuesta', sub: 'con citas' },
};

const DOC = { w: 150, h: 72, y: 24, gap: 22, max: 4 };

// Qué se enciende cuando una etapa cambia de estado.
const WIRING = {
  consulta: { done: [['consulta-recuperacion', 'done']] },
  recuperacion: {
    active: [['consulta-recuperacion', 'active'], ['indice-recuperacion', 'active']],
    done: [['consulta-recuperacion', 'done'], ['indice-recuperacion', 'done']],
  },
  modelo: { active: [['recuperacion-modelo', 'active']], done: [['recuperacion-modelo', 'done']] },
  respuesta: { done: [['modelo-respuesta', 'done']] },
};

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

const curva = (x1, y1, x2, y2, vertical) =>
  vertical
    ? `M ${x1} ${y1} C ${x1} ${y1 + 46}, ${x2} ${y2 - 46}, ${x2} ${y2}`
    : `M ${x1} ${y1} C ${x1 + 52} ${y1}, ${x2 - 52} ${y2}, ${x2} ${y2}`;

export class Flow {
  constructor(svg, { onDocumentClick } = {}) {
    this.svg = svg;
    this.onDocumentClick = onDocumentClick;
    this.documents = [];
    this.edges = new Map();
    this.nodes = new Map();
    this.primerDibujo = true;
    this.render();
  }

  // ---------------------------------------------------------------- dibujo

  render() {
    this.svg.replaceChildren();
    this.edges.clear();
    this.nodes.clear();

    this.layerEdges = el('g');
    this.layerNodes = el('g');
    this.svg.append(this.layerEdges, this.layerNodes);

    const visibles = this.documents.slice(0, DOC.max);
    const extra = this.documents.length - visibles.length;
    const total = visibles.length + (extra > 0 ? 1 : 0);

    // fila de documentos, centrada sobre el índice
    const anchoFila = total * DOC.w + Math.max(0, total - 1) * DOC.gap;
    const inicio = 480 - anchoFila / 2;

    visibles.forEach((doc, i) => {
      const x = inicio + i * (DOC.w + DOC.gap);
      this.drawDocument(doc, x);
      this.drawEdge(`doc:${doc.id}`, x + DOC.w / 2, DOC.y + DOC.h, 480, STAGES.indice.y, true);
    });

    if (extra > 0) {
      const x = inicio + visibles.length * (DOC.w + DOC.gap);
      this.drawNode('mas-docs', {
        ...DOC,
        x,
        kicker: 'biblioteca',
        title: `+${extra} más`,
        sub: 'abrir biblioteca',
      });
      this.nodes.get('mas-docs').group.classList.add('node-doc');
      this.nodes.get('mas-docs').group.addEventListener('click', () => this.onDocumentClick?.(null));
      this.drawEdge('doc:mas', x + DOC.w / 2, DOC.y + DOC.h, 480, STAGES.indice.y, true);
    }

    if (!this.documents.length) {
      const aviso = text(480, 44, 'node-sub', 'La biblioteca está vacía');
      aviso.setAttribute('text-anchor', 'middle');
      this.layerNodes.append(aviso);
    }

    for (const [id, cfg] of Object.entries(STAGES)) this.drawNode(id, cfg);

    const { indice, consulta, recuperacion, modelo, respuesta } = STAGES;
    this.drawEdge('indice-recuperacion', 480, indice.y + indice.h, recuperacion.x + 95, recuperacion.y, true);
    this.drawEdge('consulta-recuperacion', consulta.x + consulta.w, SPINE_MID, recuperacion.x, SPINE_MID, false);
    this.drawEdge('recuperacion-modelo', recuperacion.x + recuperacion.w, SPINE_MID, modelo.x, SPINE_MID, false);
    this.drawEdge('modelo-respuesta', modelo.x + modelo.w, SPINE_MID, respuesta.x, SPINE_MID, false);

    if (this.primerDibujo) {
      this.animateDrawIn();
      this.primerDibujo = false;
    }
  }

  drawNode(id, cfg) {
    const { x, y, w, h, kicker, title, sub } = cfg;
    const group = el('g', { class: 'node', 'data-id': id, 'data-state': 'idle' });

    group.append(
      el('rect', { class: 'node-box', x, y, width: w, height: h, rx: 2 }),
      el('rect', { class: 'node-tab', x, y, width: 4, height: h }),
      text(x + 15, y + 18, 'node-kicker', kicker.toUpperCase()),
      text(x + 15, y + 37, 'node-title', title),
    );

    const subtitulo = text(x + 15, y + 54, 'node-sub', sub);
    group.append(subtitulo);

    // la medición de la etapa solo cabe en los nodos altos del eje
    const detalle = text(x + 15, y + 70, 'node-sub', '');
    if (h >= SPINE_H) group.append(detalle);

    const tick = el('path', { class: 'node-tick', d: `M ${x + w - 22} ${y + 15} l 4 4 l 7 -8` });
    group.append(tick);

    this.layerNodes.append(group);
    this.nodes.set(id, { group, subtitulo, detalle, cfg });
    return group;
  }

  drawDocument(doc, x) {
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
    group.addEventListener('click', () => this.onDocumentClick?.(doc.id));

    const track = el('rect', { class: 'node-relev-track', x: x + 15, y: DOC.y + 60, width: DOC.w - 62, height: 4, rx: 1 });
    const fill = el('rect', { class: 'node-relev-fill', x: x + 15, y: DOC.y + 60, width: 0, height: 4, rx: 1 });
    const label = text(x + DOC.w - 40, DOC.y + 65, 'node-relev-label', '');

    track.setAttribute('opacity', '0');
    group.append(track, fill, label);
    Object.assign(this.nodes.get(`doc:${doc.id}`), { track, fill, label });
  }

  drawEdge(id, x1, y1, x2, y2, vertical) {
    const path = el('path', { class: 'edge', 'data-state': 'idle', d: curva(x1, y1, x2, y2, vertical) });
    this.layerEdges.append(path);
    this.edges.set(id, path);
  }

  animateDrawIn() {
    for (const path of this.edges.values()) {
      const largo = path.getTotalLength();
      path.style.setProperty('--len', largo);
      path.classList.add('flow-draw');
    }
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
      if (edge) edge.dataset.state = estado;
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

  reset() {
    for (const [id, nodo] of this.nodes) {
      if (id.startsWith('doc:') || id === 'indice' || id === 'mas-docs') continue;
      nodo.group.dataset.state = 'idle';
      if (nodo.detalle) nodo.detalle.textContent = '';
    }
    for (const [id, edge] of this.edges) {
      if (id.startsWith('doc:')) continue;
      edge.dataset.state = 'idle';
    }
  }
}

export const formatoMs = (ms) => {
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)} s`;
  return ms < 1 ? '<1 ms' : `${Math.round(ms)} ms`;
};
