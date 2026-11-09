'use strict';

function calculateOrderTotal({ lines, catalog, shipping }) {
  if (!Array.isArray(lines) || lines.length === 0 || lines.length > 100) {
    throw new Error('El carrito debe contener entre 1 y 100 líneas.');
  }
  if (!Array.isArray(catalog)) {
    throw new Error('El catálogo autorizado no está disponible.');
  }
  if (!shipping || shipping.confirmed !== true || shipping.taxesConfirmed !== true ||
      shipping.amountIncludesTaxes !== true || shipping.currency !== 'COP' ||
      !Number.isSafeInteger(shipping.amountCop) || shipping.amountCop < 0) {
    throw new Error('El envío definitivo no está confirmado.');
  }

  const resolvedLines = [];
  const seen = new Set();
  let subtotalCop = 0;
  for (const line of lines) {
    if (!line || typeof line !== 'object' ||
        Object.keys(line).some(key => !['productId', 'variantKey', 'quantity'].includes(key)) ||
        typeof line.productId !== 'string' || !line.productId ||
        typeof line.variantKey !== 'string' || !line.variantKey ||
        !Number.isSafeInteger(line.quantity) || line.quantity < 1 || line.quantity > 10000) {
      throw new Error('La línea del carrito no es válida.');
    }
    const key = JSON.stringify([line.productId, line.variantKey]);
    if (seen.has(key)) throw new Error('El carrito contiene líneas duplicadas.');
    seen.add(key);

    const matches = catalog.filter(item =>
      item && item.productId === line.productId && item.variantKey === line.variantKey
    );
    if (matches.length !== 1) throw new Error('La variante no existe o no es única en el catálogo autorizado.');
    const item = matches[0];
    if (item.available !== true || item.availabilityConfirmed !== true ||
        !Number.isSafeInteger(item.availableQuantity) || item.availableQuantity < line.quantity) {
      throw new Error('La disponibilidad del producto no está confirmada.');
    }
    if (item.priceConfirmed !== true || item.currency !== 'COP' ||
        !Number.isSafeInteger(item.unitPriceCop) || item.unitPriceCop <= 0) {
      throw new Error('El precio del producto no está confirmado.');
    }
    const knownTax = item.taxTreatment === 'excluded' || item.taxTreatment === 'exempt' ||
      (item.taxTreatment === 'taxable' && item.priceIncludesTax === true &&
        typeof item.taxRate === 'number' && Number.isFinite(item.taxRate) &&
        item.taxRate > 0 && item.taxRate <= 1);
    if (!knownTax) throw new Error('Los impuestos del producto no están confirmados.');
    const lineTotalCop = item.unitPriceCop * line.quantity;
    if (!Number.isSafeInteger(lineTotalCop) || !Number.isSafeInteger(subtotalCop + lineTotalCop)) {
      throw new Error('El subtotal excede el límite permitido.');
    }
    subtotalCop += lineTotalCop;
    resolvedLines.push({
      productId: line.productId,
      variantKey: line.variantKey,
      quantity: line.quantity,
      unitPriceCop: item.unitPriceCop,
      lineTotalCop,
      taxTreatment: item.taxTreatment
    });
  }

  const totalCop = subtotalCop + shipping.amountCop;
  const amountInCents = totalCop * 100;
  if (!Number.isSafeInteger(totalCop) || !Number.isSafeInteger(amountInCents) || amountInCents <= 0) {
    throw new Error('El total excede el límite permitido.');
  }
  return { currency: 'COP', lines: resolvedLines, subtotalCop, shippingCop: shipping.amountCop, totalCop, amountInCents };
}

module.exports = { calculateOrderTotal };
