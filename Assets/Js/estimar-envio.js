(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.NexorShipping = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function estimate(data, city, cart) {
    if (!data || !data.rates || !Array.isArray(data.eligibleProductIds)) {
      return { status: 'unavailable' };
    }
    if (!city) return { status: 'destination' };
    if (!Array.isArray(cart) || cart.length !== 1 || cart[0].quantity !== 1 || cart[0].available === false) {
      return { status: 'quantity' };
    }
    if (!data.eligibleProductIds.includes(cart[0].productId)) return { status: 'package' };
    if (!Object.prototype.hasOwnProperty.call(data.rates, city)) return { status: 'route' };
    const amount = data.rates[city];
    if (!Number.isSafeInteger(amount) || amount <= 0) return { status: 'unavailable' };
    return { status: 'reference', amount };
  }
  return { estimate };
});
