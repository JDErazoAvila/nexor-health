'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { createSandboxCheckout } = require('./wompi-sandbox.cjs');

test('genera un checkout firmado de prueba para un importe fijo', () => {
  const key = 'pub_test_example';
  const secret = 'test_integrity_example';
  const url = createSandboxCheckout(key, secret);
  const reference = url.searchParams.get('reference');
  const expected = createHash('sha256')
    .update(reference + '100000COP' + secret, 'utf8')
    .digest('hex');
  assert.equal(url.origin + url.pathname, 'https://checkout.wompi.co/p/');
  assert.equal(url.searchParams.get('public-key'), key);
  assert.equal(url.searchParams.get('currency'), 'COP');
  assert.equal(url.searchParams.get('amount-in-cents'), '100000');
  assert.match(reference, /^nexor-prueba-/);
  assert.equal(url.searchParams.get('signature:integrity'), expected);
  assert.ok(!url.href.includes(secret));
});

test('usa una referencia diferente para cada prueba', () => {
  const first = createSandboxCheckout('pub_test_example', 'test_integrity_example');
  const second = createSandboxCheckout('pub_test_example', 'test_integrity_example');
  assert.notEqual(first.searchParams.get('reference'), second.searchParams.get('reference'));
});

test('rechaza credenciales ausentes o de producción', () => {
  assert.throws(() => createSandboxCheckout(undefined, undefined), /llave pública de pruebas/);
  assert.throws(() => createSandboxCheckout('pub_prod_example', 'test_integrity_example'), /llave pública de pruebas/);
  assert.throws(() => createSandboxCheckout('pub_test_example', 'prod_integrity_example'), /secreto de integridad de pruebas/);
  assert.throws(() => createSandboxCheckout('pub_test_example', ''), /secreto de integridad de pruebas/);
});
