'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { estimate } = require('../../Assets/Js/estimar-envio.js');

const data = { rates: { '76520': 13600 }, eligibleProductIds: ['p'] };
const line = { productId: 'p', quantity: 1, available: true };
test('muestra la referencia solo para una unidad y ruta registrada', () => {
  assert.deepEqual(estimate(data, '76520', [line]), { status: 'reference', amount: 13600 });
  assert.equal(estimate(data, '', [line]).status, 'destination');
  assert.equal(estimate(data, '11001', [line]).status, 'route');
  assert.equal(estimate(data, '76520', [{ ...line, quantity: 2 }]).status, 'quantity');
  assert.equal(estimate(data, '76520', [line, line]).status, 'quantity');
  assert.equal(estimate(data, '76520', [{ ...line, available: false }]).status, 'quantity');
  assert.equal(estimate(data, '76520', [{ ...line, productId: 'other' }]).status, 'package');
  assert.equal(estimate(null, '76520', [line]).status, 'unavailable');
  assert.equal(estimate({ ...data, rates: { '76520': -1 } }, '76520', [line]).status, 'unavailable');
});
