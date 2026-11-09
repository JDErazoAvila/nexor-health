(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.NexorAI = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const config = Object.freeze({ enabled: false, endpoint: '/api/asistente' });

  async function ask(question, options) {
    if (!options.enabled) throw new Error('El asistente con IA no está habilitado.');
    if (!options.consent) throw new Error('Se necesita autorización para enviar la consulta.');
    if (typeof question !== 'string' || !question.trim() || question.length > 180) {
      throw new Error('Escribe una consulta de hasta 180 caracteres.');
    }
    const base = new URL(options.baseUrl);
    const endpoint = new URL(options.endpoint, base);
    const localHttp = base.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(base.hostname);
    if (!(base.protocol === 'https:' || localHttp) || endpoint.origin !== base.origin ||
        endpoint.username || endpoint.password || endpoint.search || endpoint.hash) {
      throw new Error('La dirección del servicio debe pertenecer al mismo sitio.');
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await options.fetch(endpoint.href, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        credentials: 'same-origin',
        redirect: 'error',
        body: JSON.stringify({ question: question.trim() }),
        signal: controller.signal
      });
      if (!response.ok) throw new Error('El servicio no pudo responder. Inténtalo más tarde.');
      const data = await response.json();
      if (!data || typeof data.answer !== 'string' || !data.answer.trim() ||
          data.answer.length > 3000 || !Array.isArray(data.productIds) ||
          data.productIds.length > 3 || !data.productIds.every(id => typeof id === 'string' && id.length <= 200)) {
        throw new Error('El servicio devolvió una respuesta inválida.');
      }
      return { answer: data.answer.trim(), productIds: [...new Set(data.productIds)] };
    } finally {
      clearTimeout(timeout);
    }
  }

  return { config, ask };
});
