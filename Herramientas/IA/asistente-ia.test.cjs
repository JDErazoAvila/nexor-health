'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { config, ask } = require('../../Assets/Js/asistente-ia.js');

const options = overrides => ({
  enabled: true,
  consent: true,
  endpoint: '/api/asistente',
  baseUrl: 'https://nexor.example/catalogo',
  fetch: async () => ({ ok: true, json: async () => ({ answer: 'Respuesta', productIds: [] }) }),
  ...overrides
});

test('la integración está desactivada por defecto y no hace solicitudes sin permiso', async () => {
  let calls = 0;
  const fetch = async () => { calls++; };
  assert.equal(config.enabled, false);
  await assert.rejects(ask('Hola', options({ enabled: false, fetch })), /no está habilitado/);
  await assert.rejects(ask('Hola', options({ consent: false, fetch })), /autorización/);
  assert.equal(calls, 0);
});

test('envía solamente la pregunta y valida la respuesta', async () => {
  const result = await ask('  ¿Tienen tensiómetros?  ', options({
    fetch: async (url, request) => {
      assert.equal(url, 'https://nexor.example/api/asistente');
      assert.equal(request.method, 'POST');
      assert.equal(request.redirect, 'error');
      assert.deepEqual(JSON.parse(request.body), { question: '¿Tienen tensiómetros?' });
      return { ok: true, json: async () => ({ answer: ' Opciones ', productIds: ['uno', 'uno', 'dos'] }) };
    }
  }));
  assert.deepEqual(result, { answer: 'Opciones', productIds: ['uno', 'dos'] });
});

test('rechaza consultas inválidas y destinos ajenos o inseguros', async () => {
  await assert.rejects(ask(' ', options()), /consulta/);
  await assert.rejects(ask('a'.repeat(181), options()), /consulta/);
  await assert.rejects(ask('Hola', options({ endpoint: 'https://otro.example/api' })), /mismo sitio/);
  await assert.rejects(ask('Hola', options({ baseUrl: 'http://nexor.example/' })), /mismo sitio/);
  await assert.rejects(ask('Hola', options({ endpoint: '/api/asistente?clave=x' })), /mismo sitio/);
});

test('permite desarrollo local sin HTTPS', async () => {
  const result = await ask('Hola', options({ baseUrl: 'http://127.0.0.1:8000/' }));
  assert.equal(result.answer, 'Respuesta');
});

test('propaga errores del servicio y rechaza respuestas inesperadas', async () => {
  await assert.rejects(ask('Hola', options({ fetch: async () => ({ ok: false }) })), /no pudo responder/);
  for (const data of [
    { answer: '', productIds: [] },
    { answer: 'Hola', productIds: [1] },
    { answer: 'Hola', productIds: ['a', 'b', 'c', 'd'] },
    { answer: 'a'.repeat(3001), productIds: [] }
  ]) {
    await assert.rejects(ask('Hola', options({
      fetch: async () => ({ ok: true, json: async () => data })
    })), /respuesta inválida/);
  }
});
