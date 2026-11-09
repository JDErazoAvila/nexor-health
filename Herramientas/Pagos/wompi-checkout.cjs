'use strict';

const { createHash } = require('node:crypto');

function createCheckoutUrl({ publicKey, integritySecret, reference, amountInCents, environment }) {
  if (!['sandbox', 'production'].includes(environment)) {
    throw new Error('El ambiente de Wompi debe ser sandbox o production.');
  }
  const keyPattern = environment === 'sandbox' ? /^pub_test_[A-Za-z0-9_-]+$/ : /^pub_prod_[A-Za-z0-9_-]+$/;
  const secretPattern = environment === 'sandbox' ? /^test_integrity_[A-Za-z0-9_-]+$/ : /^prod_integrity_[A-Za-z0-9_-]+$/;
  if (typeof publicKey !== 'string' || !keyPattern.test(publicKey)) {
    throw new Error('La llave pública no corresponde al ambiente de Wompi.');
  }
  if (typeof integritySecret !== 'string' || !secretPattern.test(integritySecret)) {
    throw new Error('El secreto de integridad no corresponde al ambiente de Wompi.');
  }
  if (typeof reference !== 'string' || !/^[A-Za-z0-9_-]{1,100}$/.test(reference)) {
    throw new Error('La referencia de pago no es válida.');
  }
  if (!Number.isSafeInteger(amountInCents) || amountInCents <= 0) {
    throw new Error('El monto en centavos debe ser un entero positivo seguro.');
  }
  const currency = 'COP';
  const signature = createHash('sha256')
    .update(reference + amountInCents + currency + integritySecret, 'utf8')
    .digest('hex');
  const checkout = new URL('https://checkout.wompi.co/p/');
  checkout.searchParams.set('public-key', publicKey);
  checkout.searchParams.set('currency', currency);
  checkout.searchParams.set('amount-in-cents', String(amountInCents));
  checkout.searchParams.set('reference', reference);
  checkout.searchParams.set('signature:integrity', signature);
  return checkout;
}

module.exports = { createCheckoutUrl };
