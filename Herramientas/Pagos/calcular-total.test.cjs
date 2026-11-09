'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { calculateOrderTotal } = require('./calcular-total.cjs');

const line = { productId: 'p', variantKey: 'p::ref::azul', quantity: 2 };
const product = {
  productId: 'p', variantKey: 'p::ref::azul', available: true, availabilityConfirmed: true, availableQuantity: 2,
  priceConfirmed: true, currency: 'COP', unitPriceCop: 50000, taxTreatment: 'taxable',
  priceIncludesTax: true, taxRate: 0.19
};
const shipping = { confirmed: true, taxesConfirmed: true, amountIncludesTaxes: true, currency: 'COP', amountCop: 13600 };
const args = () => ({ lines: [{ ...line }], catalog: [{ ...product }], shipping: { ...shipping } });

test('calcula el total definitivo en pesos y centavos con impuestos incluidos', () => {
  const result = calculateOrderTotal(args());
  assert.equal(result.subtotalCop, 100000);
  assert.equal(result.shippingCop, 13600);
  assert.equal(result.totalCop, 113600);
  assert.equal(result.amountInCents, 11360000);
  assert.deepEqual(result.lines[0], {
    productId: 'p', variantKey: 'p::ref::azul', quantity: 2,
    unitPriceCop: 50000, lineTotalCop: 100000, taxTreatment: 'taxable'
  });
});

test('suma variantes diferentes usando exclusivamente los precios del catálogo', () => {
  const secondLine = { productId: 'q', variantKey: 'q::ref::verde', quantity: 3 };
  const secondProduct = {
    ...product, productId: 'q', variantKey: secondLine.variantKey,
    availableQuantity: 3, unitPriceCop: 12500, taxTreatment: 'exempt'
  };
  const result = calculateOrderTotal({
    lines: [line, secondLine], catalog: [product, secondProduct], shipping
  });
  assert.equal(result.subtotalCop, 137500);
  assert.equal(result.totalCop, 151100);
  assert.equal(result.amountInCents, 15110000);
});

test('rechaza precios del cliente, líneas duplicadas y cantidades inválidas', () => {
  for (const lines of [
    [], [{ ...line, unitPriceCop: 1 }], [line, line],
    [{ ...line, quantity: 0 }], [{ ...line, quantity: 10001 }],
    [{ ...line, quantity: 1.5 }], [{ ...line, productId: '' }]
  ]) {
    assert.throws(() => calculateOrderTotal({ ...args(), lines }));
  }
});

test('requiere variante única, precio y disponibilidad confirmados', () => {
  for (const catalog of [
    [], [product, product], [{ ...product, available: false }],
    [{ ...product, availabilityConfirmed: false }], [{ ...product, availableQuantity: 1 }],
    [{ ...product, availableQuantity: 2.5 }], [{ ...product, priceConfirmed: false }],
    [{ ...product, currency: 'USD' }], [{ ...product, unitPriceCop: 0 }],
    [{ ...product, unitPriceCop: 1.5 }]
  ]) {
    assert.throws(() => calculateOrderTotal({ ...args(), catalog }));
  }
});

test('rechaza impuestos pendientes o no incluidos y admite tratamientos confirmados', () => {
  for (const change of [
    { taxTreatment: 'pending' }, { priceIncludesTax: false }, { taxRate: 0 },
    { taxRate: 2 }, { taxRate: NaN }
  ]) {
    assert.throws(() => calculateOrderTotal({ ...args(), catalog: [{ ...product, ...change }] }), /impuestos/);
  }
  for (const taxTreatment of ['excluded', 'exempt']) {
    const result = calculateOrderTotal({ ...args(), catalog: [{ ...product, taxTreatment }] });
    assert.equal(result.totalCop, 113600);
  }
});

test('rechaza envío orientativo, moneda equivocada y desbordamientos', () => {
  for (const value of [
    null, { ...shipping, confirmed: false }, { ...shipping, taxesConfirmed: false },
    { ...shipping, amountIncludesTaxes: false }, { ...shipping, currency: 'USD' },
    { ...shipping, amountCop: -1 }, { ...shipping, amountCop: 1.5 },
    { ...shipping, amountCop: Number.MAX_SAFE_INTEGER }
  ]) {
    assert.throws(() => calculateOrderTotal({ ...args(), shipping: value }));
  }
  assert.throws(() => calculateOrderTotal({
    ...args(), catalog: [{ ...product, unitPriceCop: Number.MAX_SAFE_INTEGER }]
  }), /límite/);
  assert.equal(calculateOrderTotal({ ...args(), shipping: { ...shipping, amountCop: 0 } }).totalCop, 100000);
});
