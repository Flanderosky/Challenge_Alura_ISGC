// Cliente HTTP. Nada de estado aquí: solo hablar con el backend.

async function json(response) {
  const cuerpo = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(cuerpo.detail || `Error ${response.status}`);
  return cuerpo;
}

export const api = {
  state: () => fetch('/api/state').then(json),

  addDocument(file) {
    const cuerpo = new FormData();
    cuerpo.append('file', file);
    return fetch('/api/documents', { method: 'POST', body: cuerpo }).then(json);
  },

  removeDocument: (id) => fetch(`/api/documents/${id}`, { method: 'DELETE' }).then(json),

  content: (id, page) =>
    fetch(`/api/documents/${id}/content${page ? `?page=${page}` : ''}`).then(json),
};

/**
 * Abre /api/query y entrega cada evento del pipeline en cuanto llega.
 * El backend habla SSE; aquí se corta el flujo por eventos completos.
 */
export async function* streamQuery({ question, history, signal }) {
  const respuesta = await fetch('/api/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, history }),
    signal,
  });

  if (!respuesta.ok || !respuesta.body) {
    throw new Error('El servidor no aceptó la consulta.');
  }

  const lector = respuesta.body.getReader();
  const decoder = new TextDecoder();
  let pendiente = '';

  while (true) {
    const { value, done } = await lector.read();
    if (done) break;

    pendiente += decoder.decode(value, { stream: true });
    const bloques = pendiente.split('\n\n');
    pendiente = bloques.pop() ?? '';

    for (const bloque of bloques) {
      const linea = bloque.split('\n').find((l) => l.startsWith('data:'));
      if (!linea) continue;
      try {
        yield JSON.parse(linea.slice(5).trim());
      } catch {
        /* evento partido o malformado: se ignora y sigue el flujo */
      }
    }
  }
}
