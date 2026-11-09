'use strict';

const { createHash, randomUUID } = require('node:crypto');

const TEST_AMOUNT_IN_CENTS = 100000;
const CURRENCY = 'COP';

function createSandboxCheckout(publicKey, integritySecret) {
  if (typeof publicKey !== 'string' || !/^pub_test_[A-Za-z0-9_-]+$/.test(publicKey)) {
    throw new Error('Se requiere una llave pública de pruebas válida con prefijo pub_test_.');
  }
  if (typeof integritySecret !== 'string' || !/^test_integrity_[A-Za-z0-9_-]+$/.test(integritySecret)) {
    throw new Error('Se requiere un secreto de integridad de pruebas válido con prefijo test_integrity_.');
  }

  const reference = 'nexor-prueba-' + randomUUID();
  const signature = createHash('sha256')
    .update(reference + TEST_AMOUNT_IN_CENTS + CURRENCY + integritySecret, 'utf8')
    .digest('hex');
  const checkout = new URL('https://checkout.wompi.co/p/');
  checkout.searchParams.set('public-key', publicKey);
  checkout.searchParams.set('currency', CURRENCY);
  checkout.searchParams.set('amount-in-cents', String(TEST_AMOUNT_IN_CENTS));
  checkout.searchParams.set('reference', reference);
  checkout.searchParams.set('signature:integrity', signature);
  return checkout;
}

if (require.main === module) {
  try {
    const checkout = createSandboxCheckout(
      process.env.WOMPI_SANDBOX_PUBLIC_KEY,
      process.env.WOMPI_SANDBOX_INTEGRITY_SECRET
    );
    console.log('Prueba ficticia de Wompi Sandbox: $1.000 COP. No es un pedido real.');
    console.log('Abra el siguiente enlace únicamente para realizar la prueba:');
    console.log(checkout.href);
    console.log('El resultado debe verificarse en Wompi; esta herramienta no confirma pagos.');
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}

module.exports = { createSandboxCheckout };
