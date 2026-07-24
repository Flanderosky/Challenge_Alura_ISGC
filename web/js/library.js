// Cajón de la biblioteca: lista de documentos, alta, baja y visor con la
// evidencia resaltada sobre el texto original.

import { api } from './api.js';

const PESO = (bytes) =>
  bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;

const escapar = (texto) =>
  texto.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export class LibraryDrawer {
  constructor({ onChange }) {
    this.onChange = onChange;
    this.documents = [];
    this.abierto = false;

    this.drawer = document.getElementById('drawer');
    this.scrim = document.getElementById('scrim');
    this.title = document.getElementById('drawer-title');
    this.back = document.getElementById('drawer-back');
    this.viewLibrary = document.getElementById('view-library');
    this.viewViewer = document.getElementById('view-viewer');
    this.list = document.getElementById('doc-list');
    this.msg = document.getElementById('library-msg');
    this.dropzone = document.getElementById('dropzone');
    this.fileInput = document.getElementById('file-input');
    this.viewerMeta = document.getElementById('viewer-meta');
    this.viewerPage = document.getElementById('viewer-page');
    this.viewerPos = document.getElementById('viewer-pos');

    this.bind();
  }

  bind() {
    document.getElementById('open-library').addEventListener('click', () => this.open());
    document.getElementById('drawer-close').addEventListener('click', () => this.close());
    this.scrim.addEventListener('click', () => this.close());
    this.back.addEventListener('click', () => this.showList());

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.abierto) this.close();
    });

    this.dropzone.addEventListener('click', () => this.fileInput.click());
    this.fileInput.addEventListener('change', () => {
      if (this.fileInput.files?.[0]) this.upload(this.fileInput.files[0]);
      this.fileInput.value = '';
    });

    for (const evento of ['dragenter', 'dragover']) {
      this.dropzone.addEventListener(evento, (e) => {
        e.preventDefault();
        this.dropzone.dataset.over = 'true';
      });
    }
    for (const evento of ['dragleave', 'drop']) {
      this.dropzone.addEventListener(evento, (e) => {
        e.preventDefault();
        this.dropzone.dataset.over = 'false';
      });
    }
    this.dropzone.addEventListener('drop', (e) => {
      const archivo = e.dataTransfer?.files?.[0];
      if (archivo) this.upload(archivo);
    });

    document.getElementById('page-prev').addEventListener('click', () => this.turnPage(-1));
    document.getElementById('page-next').addEventListener('click', () => this.turnPage(1));
  }

  // ------------------------------------------------------------------ cajón

  open() {
    this.abierto = true;
    this.drawer.hidden = false;
    this.scrim.hidden = false;
    this.showList();
    this.drawer.querySelector('.dropzone')?.focus?.();
  }

  close() {
    this.abierto = false;
    this.drawer.hidden = true;
    this.scrim.hidden = true;
  }

  showList() {
    this.title.textContent = 'Biblioteca';
    this.back.hidden = true;
    this.viewLibrary.hidden = false;
    this.viewViewer.hidden = true;
  }

  showViewer() {
    this.back.hidden = false;
    this.viewLibrary.hidden = true;
    this.viewViewer.hidden = false;
  }

  error(texto) {
    this.msg.hidden = !texto;
    this.msg.textContent = texto ?? '';
  }

  // --------------------------------------------------------------- listado

  setDocuments(documentos) {
    this.documents = documentos;
    this.list.replaceChildren();

    if (!documentos.length) {
      const vacio = document.createElement('li');
      vacio.className = 'list-empty';
      vacio.textContent =
        'La biblioteca está vacía. Agrega un PDF o CSV para que el agente tenga de dónde responder.';
      this.list.append(vacio);
      return;
    }

    for (const doc of documentos) {
      const fila = document.createElement('li');
      fila.className = 'doc-row';

      const tipo = document.createElement('span');
      tipo.className = 'doc-kind';
      tipo.textContent = doc.kind.toUpperCase();

      const principal = document.createElement('button');
      principal.className = 'doc-main';
      principal.innerHTML = `
        <div class="doc-name">${escapar(doc.filename)}</div>
        <div class="doc-facts">${doc.chunks} fragmentos · ${doc.units} ${
        doc.kind === 'pdf' ? 'páginas' : 'bloques'
      } · ${PESO(doc.bytes)}</div>`;
      principal.addEventListener('click', () => this.openDocument(doc.id));

      const quitar = document.createElement('button');
      quitar.className = 'btn-remove';
      quitar.textContent = 'Quitar';
      quitar.addEventListener('click', () => this.remove(doc, quitar));

      fila.append(tipo, principal, quitar);
      this.list.append(fila);
    }
  }

  async upload(archivo) {
    this.error(null);
    this.dropzone.dataset.busy = 'true';
    const lead = this.dropzone.querySelector('.dropzone-lead');
    const original = lead.textContent;
    lead.textContent = `Indexando ${archivo.name}…`;

    try {
      const respuesta = await api.addDocument(archivo);
      this.onChange(respuesta.state);
    } catch (e) {
      this.error(e.message);
    } finally {
      this.dropzone.dataset.busy = 'false';
      lead.textContent = original;
    }
  }

  async remove(doc, boton) {
    // Confirmación en dos toques: el segundo clic borra.
    if (boton.dataset.confirm !== 'true') {
      boton.dataset.confirm = 'true';
      boton.textContent = 'Confirmar';
      setTimeout(() => {
        boton.dataset.confirm = 'false';
        boton.textContent = 'Quitar';
      }, 3500);
      return;
    }

    this.error(null);
    boton.disabled = true;
    boton.textContent = 'Quitando…';
    try {
      const respuesta = await api.removeDocument(doc.id);
      this.onChange(respuesta.state);
    } catch (e) {
      this.error(e.message);
      boton.disabled = false;
      boton.textContent = 'Quitar';
    }
  }

  // ----------------------------------------------------------------- visor

  /** Abre un documento. Si se pasa `highlight`, resalta ese pasaje en la página. */
  async openDocument(docId, { page, highlight } = {}) {
    if (!docId) {
      this.open();
      return;
    }
    this.open();
    this.showViewer();
    this.viewer = { docId, highlight };
    this.viewerPage.textContent = 'Abriendo…';
    await this.loadPage(page);
  }

  async loadPage(page) {
    try {
      const datos = await api.content(this.viewer.docId, page);
      this.viewer.page = datos.page;
      this.viewer.total = datos.total_pages;
      this.title.textContent = datos.filename;
      this.viewerMeta.textContent = `${datos.kind.toUpperCase()} · ${datos.total_pages} ${datos.unit}s`;
      this.viewerPos.textContent = `${datos.unit} ${datos.page} de ${datos.total_pages}`;
      this.viewerPage.innerHTML = this.markup(datos.text, this.viewer.highlight);
      document.getElementById('page-prev').disabled = datos.page <= 1;
      document.getElementById('page-next').disabled = datos.page >= datos.total_pages;
      this.viewerPage.querySelector('mark')?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    } catch (e) {
      this.viewerPage.textContent = `No se pudo abrir el documento: ${e.message}`;
    }
  }

  turnPage(delta) {
    const destino = (this.viewer?.page ?? 1) + delta;
    if (destino < 1 || destino > (this.viewer?.total ?? 1)) return;
    this.viewer.highlight = null;
    this.loadPage(destino);
  }

  /**
   * Resalta el fragmento recuperado dentro del texto de la página.
   * El fragmento salió de este mismo texto, así que casi siempre coincide
   * literal; si no, se busca su primera línea antes de rendirse.
   */
  markup(texto, highlight) {
    if (!highlight) return escapar(texto);

    const candidatos = [highlight.trim(), highlight.trim().split('\n')[0]];
    for (const aguja of candidatos) {
      if (aguja.length < 12) continue;
      const desde = texto.indexOf(aguja);
      if (desde === -1) continue;
      return (
        escapar(texto.slice(0, desde)) +
        `<mark>${escapar(texto.slice(desde, desde + aguja.length))}</mark>` +
        escapar(texto.slice(desde + aguja.length))
      );
    }
    return escapar(texto);
  }
}
