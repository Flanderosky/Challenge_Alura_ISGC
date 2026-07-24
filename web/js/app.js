// Orquestación: estado de la biblioteca, hilo de consulta y sincronía con el
// lienzo del recorrido.

import { api, streamQuery } from './api.js';
import { Flow, formatoMs } from './flow.js';
import { LibraryDrawer } from './library.js';

const $ = (id) => document.getElementById(id);

const ETIQUETA_ESTADO = {
  listo: 'listo',
  indexando: 'construyendo',
  vacio: 'vacío',
  error: 'error',
};

const NOTA_ETAPA = {
  consulta: 'Vectorizando la pregunta',
  recuperacion: 'Buscando en el índice',
  modelo: 'Redactando la respuesta',
};

const escapar = (t) => t.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

const app = {
  state: null,
  history: [],
  hits: [],
  ocupado: false,
};

const library = new LibraryDrawer({ onChange: (estado) => aplicarEstado(estado) });
const flow = new Flow($('flow-svg'), {
  onDocumentClick: (docId) => library.openDocument(docId),
  onDocumentHover: (docId, activo) => {
    flow.highlightDocument(docId, activo);
    for (const fila of document.querySelectorAll(`.source[data-doc="${docId}"]`)) {
      fila.toggleAttribute('data-on', activo);
    }
  },
});

// ─────────────────────────────────────────────────────────── estado global

function aplicarEstado(estado) {
  app.state = estado;

  $('index-status').textContent = ETIQUETA_ESTADO[estado.status] ?? estado.status;
  $('index-status').dataset.status = estado.status;
  $('chunk-count').textContent = estado.chunk_count || '—';
  $('model-name').textContent = estado.model ?? '—';
  $('doc-count').textContent = estado.documents.length;

  flow.setDocuments(estado.documents);
  flow.setIndex({
    status: estado.status,
    chunks: estado.chunk_count,
    documents: estado.documents.length,
  });
  flow.setModel(estado.model ?? '—');
  library.setDocuments(estado.documents);

  pintarSugerencias();
  $('send').disabled = app.ocupado || estado.status !== 'listo';
}

async function refrescarEstado() {
  try {
    aplicarEstado(await api.state());
  } catch {
    $('index-status').textContent = 'sin conexión';
    $('index-status').dataset.status = 'error';
  }
}

/** Mientras el índice se construye, el estado se refresca solo. */
function vigilarIndice() {
  setInterval(() => {
    if (app.state?.status === 'indexando' && !app.ocupado) refrescarEstado();
  }, 1500);
}

// ───────────────────────────────────────────────────────────── sugerencias

function pintarSugerencias() {
  const nombres = (app.state?.documents ?? []).map((d) => d.filename.toLowerCase());
  const sugerencias = [];

  if (nombres.some((n) => n.includes('politica'))) {
    sugerencias.push('¿Cuántos días de vacaciones corresponden por año?', '¿Qué dice la política de trabajo remoto?');
  }
  if (nombres.some((n) => n.includes('venta'))) {
    sugerencias.push('¿Cuál fue el total de ventas y el producto más vendido?');
  }
  if (!sugerencias.length && app.state?.documents.length) {
    sugerencias.push('¿De qué trata este documento?', 'Resume los puntos principales.');
  }

  const contenedor = $('starters');
  contenedor.replaceChildren();
  for (const texto of sugerencias.slice(0, 3)) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'starter';
    chip.textContent = texto;
    chip.addEventListener('click', () => enviar(texto));
    contenedor.append(chip);
  }
}

// ─────────────────────────────────────────────────────────────────── hilo

function nuevoTurno(rol, kicker) {
  $('thread-empty')?.remove();
  $('clear-thread').hidden = false;

  const turno = document.createElement('article');
  turno.className = `turn turn-${rol}`;

  const etiqueta = document.createElement('div');
  etiqueta.className = 'turn-kicker';
  etiqueta.textContent = kicker;

  const cuerpo = document.createElement('div');
  cuerpo.className = 'turn-body';

  turno.append(etiqueta, cuerpo);
  $('thread').append(turno);
  $('thread').scrollTop = $('thread').scrollHeight;
  return { turno, cuerpo, etiqueta };
}

/** Markdown mínimo: párrafos, viñetas, negrita y las citas [n] como fichas. */
function renderRespuesta(texto) {
  return texto
    .split(/\n{2,}/)
    .map((bloque) => {
      const lineas = bloque.split('\n');
      if (lineas.every((l) => /^\s*[-*]\s+/.test(l))) {
        const items = lineas.map((l) => `<li>${enriquecer(l.replace(/^\s*[-*]\s+/, ''))}</li>`).join('');
        return `<ul>${items}</ul>`;
      }
      return `<p>${enriquecer(bloque.replace(/\n/g, ' '))}</p>`;
    })
    .join('');
}

const enriquecer = (texto) =>
  escapar(texto)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\[(\d+)\]/g, '<button type="button" class="cite" data-n="$1">$1</button>');

function pintarEvidencia(contenedor, hits) {
  if (!hits.length) return;

  const bloque = document.createElement('div');
  bloque.className = 'evidence';

  const titulo = document.createElement('div');
  titulo.className = 'evidence-head';
  titulo.textContent = `Evidencia · ${hits.length} fragmentos`;
  bloque.append(titulo);

  for (const hit of hits) {
    const fila = document.createElement('button');
    fila.type = 'button';
    fila.className = 'source';
    fila.dataset.n = hit.n;
    fila.dataset.doc = hit.doc_id;
    fila.addEventListener('mouseenter', () => flow.highlightDocument(hit.doc_id, true));
    fila.addEventListener('mouseleave', () => flow.highlightDocument(hit.doc_id, false));
    fila.innerHTML = `
      <span class="source-n">[${hit.n}]</span>
      <span class="source-where">${escapar(hit.filename ?? 'documento')} <em>${escapar(hit.locator ?? '')}</em></span>
      <span class="source-score">
        <span class="score-bar"><span class="score-fill" style="width:${Math.round(hit.score * 100)}%"></span></span>
        <span class="score-num">${Math.round(hit.score * 100)}%</span>
      </span>`;
    fila.addEventListener('click', () => abrirFuente(hit));
    bloque.append(fila);
  }

  contenedor.append(bloque);
}

const DERIVADOS = new Set(['summary', 'breakdown']);

function abrirFuente(hit) {
  if (DERIVADOS.has(hit.unit)) {
    library.showDerived(hit);
    return;
  }
  library.openDocument(hit.doc_id, { page: hit.page, highlight: hit.text });
}

// ──────────────────────────────────────────────────────────────── consulta

async function enviar(pregunta) {
  const texto = pregunta.trim();
  if (!texto || app.ocupado || app.state?.status !== 'listo') return;

  app.ocupado = true;
  $('send').disabled = true;
  $('question').value = '';
  ajustarAltura();

  nuevoTurno('user', 'Tú').cuerpo.textContent = texto;
  const agente = nuevoTurno('agent', 'Agente');
  agente.cuerpo.classList.add('caret');

  flow.reset();
  reiniciarTelemetria();
  flow.setStage('consulta', 'active');
  $('flow-note').textContent = 'Vectorizando la pregunta';
  $('flow-note').dataset.live = 'true';

  let respuesta = '';
  app.hits = [];

  try {
    for await (const evento of streamQuery({ question: texto, history: app.history })) {
      switch (evento.type) {
        case 'stage':
          flow.setStage(evento.id, evento.status, { ...(evento.meta ?? {}), ms: evento.ms });
          if (evento.status === 'active' && NOTA_ETAPA[evento.id]) {
            $('flow-note').textContent = NOTA_ETAPA[evento.id];
          }
          if (evento.ms != null) fijarTelemetria(evento.id, evento.ms);
          break;

        case 'hits':
          app.hits = evento.hits;
          flow.setContributions(evento.contributions);
          flow.setHits(evento.hits);
          flow.pulseDocuments(evento.contributions);
          break;

        case 'token':
          respuesta += evento.text;
          agente.cuerpo.innerHTML = renderRespuesta(respuesta);
          $('thread').scrollTop = $('thread').scrollHeight;
          break;

        case 'done':
          respuesta = evento.answer || respuesta;
          agente.cuerpo.classList.remove('caret');
          agente.cuerpo.innerHTML = renderRespuesta(respuesta);
          pintarEvidencia(agente.turno, app.hits);
          conectarCitas(agente.turno);
          volcarTelemetria(evento.timings);
          pintarTimeline(evento.timings);
          $('flow-note').textContent = `Listo en ${formatoMs(evento.timings.total)}`;
          $('flow-note').dataset.live = 'false';
          app.history.push({ role: 'user', content: texto }, { role: 'assistant', content: respuesta });
          break;

        case 'error':
          throw new Error(evento.message);
      }
    }
  } catch (e) {
    agente.cuerpo.classList.remove('caret');
    agente.cuerpo.innerHTML = '';
    const aviso = document.createElement('div');
    aviso.className = 'turn-error';
    aviso.textContent = e.message;
    agente.cuerpo.append(aviso);
    flow.reset();
    $('flow-note').textContent = 'La consulta se detuvo';
    $('flow-note').dataset.live = 'false';
  } finally {
    app.ocupado = false;
    $('send').disabled = app.state?.status !== 'listo';
    $('question').focus();
  }
}

/** Al pasar por una cita, se ilumina su fila de evidencia; al hacer clic, se abre. */
function conectarCitas(turno) {
  for (const cita of turno.querySelectorAll('.cite')) {
    const n = Number(cita.dataset.n);
    const fila = turno.querySelector(`.source[data-n="${n}"]`);
    const hit = app.hits.find((h) => h.n === n);

    cita.addEventListener('mouseenter', () => fila?.setAttribute('data-on', 'true'));
    cita.addEventListener('mouseleave', () => fila?.removeAttribute('data-on'));
    cita.addEventListener('click', () => hit && abrirFuente(hit));
  }
}

// ──────────────────────────────────────────────────────────── telemetría

const CLAVE_TELEMETRIA = { consulta: 'embedding', recuperacion: 'busqueda', modelo: 'modelo' };

function reiniciarTelemetria() {
  for (const dd of document.querySelectorAll('[data-tele]')) dd.textContent = '—';
  for (const seg of document.querySelectorAll('.seg')) seg.style.width = '0%';
}

/** Las tres etapas medidas, a escala, sobre el ancho del panel. */
function pintarTimeline(timings) {
  const partes = ['embedding', 'busqueda', 'modelo'];
  const total = partes.reduce((suma, clave) => suma + (timings[clave] ?? 0), 0);
  if (!total) return;
  for (const clave of partes) {
    const seg = document.querySelector(`.seg[data-seg="${clave}"]`);
    if (seg) seg.style.width = `${((timings[clave] ?? 0) / total) * 100}%`;
  }
}

function fijarTelemetria(etapa, ms) {
  const clave = CLAVE_TELEMETRIA[etapa];
  const dd = clave && document.querySelector(`[data-tele="${clave}"]`);
  if (dd) dd.textContent = formatoMs(ms);
}

function volcarTelemetria(timings) {
  for (const [clave, valor] of Object.entries(timings)) {
    const dd = document.querySelector(`[data-tele="${clave}"]`);
    if (dd) dd.textContent = valor == null ? '—' : formatoMs(valor);
  }
}

// ─────────────────────────────────────────────────────────────── redactor

function ajustarAltura() {
  const campo = $('question');
  campo.style.height = 'auto';
  campo.style.height = `${Math.min(campo.scrollHeight, 140)}px`;
}

$('composer').addEventListener('submit', (e) => {
  e.preventDefault();
  enviar($('question').value);
});

$('question').addEventListener('input', ajustarAltura);

$('question').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    enviar($('question').value);
  }
});

$('clear-thread').addEventListener('click', () => {
  if (app.ocupado) return;
  app.history = [];
  app.hits = [];
  $('thread').replaceChildren(plantillaVacia());
  $('clear-thread').hidden = true;
  flow.reset();
  flow.setContributions([]);
  reiniciarTelemetria();
  $('flow-note').textContent = 'En reposo';
  $('flow-note').dataset.live = 'false';
  pintarSugerencias();
});

/** Estado inicial del hilo, reconstruido tal cual lo entrega el HTML. */
function plantillaVacia() {
  const vacio = document.createElement('div');
  vacio.className = 'thread-empty';
  vacio.id = 'thread-empty';
  vacio.innerHTML = `
    <p class="empty-lead">Pregúntale a tus documentos.</p>
    <p class="empty-help">Cada respuesta se construye solo con lo que hay en la biblioteca, y viene con las fuentes que la sostienen.</p>
    <div class="starters" id="starters"></div>`;
  return vacio;
}

// ──────────────────────────────────────────────────────────────── arranque

refrescarEstado();
vigilarIndice();
