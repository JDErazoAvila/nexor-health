'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { createCheckoutUrl } = require('./wompi-checkout.cjs');

const sandbox = {
  environment: 'sandbox',
  publicKey: 'pub_test_example',
  integritySecret: 'test_integrity_example',
  reference: 'nexor_123',
  amountInCents: 150000
};

test('firma el checkout oficial con datos validados y sin incluir el secreto', () => {
  const url = createCheckoutUrl(sandbox);
  const signature = createHash('sha256').update('nexor_123150000COPtest_integrity_example').digest('hex');
  assert.equal(url.origin + url.pathname, 'https://checkout.wompi.co/p/');
  assert.equal(url.searchParams.get('signature:integrity'), signature);
  assert.equal(url.searchParams.get('amount-in-cents'), '150000');
  assert.equal(url.searchParams.get('reference'), 'nexor_123');
  assert.ok(!url.href.includes(sandbox.integritySecret));
});

test('rechaza ambientes y credenciales mezclados', () => {
  assert.throws(() => createCheckoutUrl({ ...sandbox, environment: 'other' }), /ambiente/);
  assert.throws(() => createCheckoutUrl({ ...sandbox, publicKey: 'pub_prod_x' }), /llave pública/);
  assert.throws(() => createCheckoutUrl({ ...sandbox, integritySecret: 'prod_integrity_x' }), /secreto/);
  assert.throws(() => createCheckoutUrl({ ...sandbox, environment: 'production' }), /llave pública/);
  const production = { ...sandbox, environment: 'production', publicKey: 'pub_prod_x', integritySecret: 'prod_integrity_x' };
  assert.equal(createCheckoutUrl(production).searchParams.get('public-key'), 'pub_prod_x');
});

test('rechaza montos y referencias no válidos', () => {
  for (const amountInCents of [0, -1, 1.5, NaN, Number.MAX_SAFE_INTEGER + 1, '100']) {
    assert.throws(() => createCheckoutUrl({ ...sandbox, amountInCents }), /monto/);
  }
  for (const reference of ['', 'a b', 'a&b', 'x'.repeat(101)]) {
    assert.throws(() => createCheckoutUrl({ ...sandbox, reference }), /referencia/);
  }
});
