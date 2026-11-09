'use strict';

const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.join(__dirname, '..', '..');
const groups = {
  pequeno: [
    'Fonendoscopios', 'Medias de compresión', 'Medias de compresión deportivas',
    'Panty medias de compresión', 'Panty medias con compresión', 'Medias para diabéticos',
    'Pulsioxímetros', 'Termómetros digitales', 'Cintas métricas', 'Torniquetes',
    'Linternas de diagnóstico', 'Gorros médicos', 'Tijeras'
  ],
  mediano: [
    'Kit de tensiómetros y fonendoscopios', 'Tensiómetros digitales', 'Tensiómetros',
    'Compresores nebulizadores', 'Kit de órganos y sentidos'
  ],
  grande: ['Caminadores estándar', 'Caminadores con ruedas'],
  voluminoso: [
    'Sillas de ruedas de transporte', 'Sillas de ruedas estándar',
    'Sillas de ruedas motorizadas', 'silla de ruedas activa', 'Cama hospitalaria',
    'Grúa Hidráulica'
  ]
};
const departmentRegions = {
  '05': 'Antioquia',
  '08': 'Caribe', '13': 'Caribe', '20': 'Caribe', '23': 'Caribe',
  '44': 'Caribe', '47': 'Caribe', '70': 'Caribe',
  '11': 'Centro', '15': 'Centro', '25': 'Centro', '41': 'Centro', '73': 'Centro',
  '17': 'Eje cafetero', '63': 'Eje cafetero', '66': 'Eje cafetero',
  '76': 'Valle del Cauca'
};
const localCodes = new Set(['76001', '76892', '76364']);

function readWindowData(relativePath, property) {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync(path.join(root, relativePath), 'utf8'), context);
  const data = context.window[property];
  if (!Array.isArray(data) || !data.length) throw new Error('Datos ausentes: ' + relativePath);
  return data;
}

function csvCell(value) {
  const text = String(value ?? '');
  return /[;"\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
}

function csv(rows) {
  return rows.map(row => row.map(csvCell).join(';')).join('\n') + '\n';
}

function writeNewFile(name, rows) {
  const destination = path.join(root, 'Datos', name);
  fs.writeFileSync(destination, '\uFEFF' + csv(rows), { encoding: 'utf8', flag: 'wx' });
  console.log('Creado: ' + destination + ' (' + (rows.length - 1) + ' registros).');
}

function main() {
  const products = readWindowData('Assets\\Js\\catalogo-productos.js', 'NEXOR_PRODUCTS');
  const departments = readWindowData('Assets\\Js\\municipios-colombia.js', 'NEXOR_LOCATIONS');
  const manual = JSON.parse(fs.readFileSync(path.join(root, 'Datos', 'clasificacion-envios.json'), 'utf8'));
  const assignments = new Map(manual.productos.map(item => [item.id, item]));
  const groupByType = new Map();
  for (const [group, types] of Object.entries(groups)) {
    for (const type of types) {
      if (groupByType.has(type)) throw new Error('Tipo duplicado: ' + type);
      groupByType.set(type, group);
    }
  }
  const productIds = new Set();
  const productRows = [['id_producto', 'nombre', 'tipo', 'grupo_preliminar', 'estado', 'peso_empacado_kg', 'largo_cm', 'ancho_cm', 'alto_cm', 'fuente_medidas', 'observaciones']];
  for (const product of products) {
    if (!product.id || productIds.has(product.id)) throw new Error('ID de producto ausente o duplicado: ' + product.id);
    productIds.add(product.id);
    const assigned = assignments.get(product.id);
    const group = assigned?.grupo || groupByType.get(product.productType) || '';
    const observation = assigned?.observaciones || (group
      ? 'Clasificación orientativa por tipo. Confirmar peso, dimensiones y embalaje antes de cotizar.'
      : 'Sin clasificación. Revisar presentación, embalaje, peso y dimensiones.');
    productRows.push([product.id, product.name, product.productType, group, group ? 'provisional' : 'pendiente', '', '', '', '', '', observation]);
  }
  for (const id of assignments.keys()) {
    if (!productIds.has(id)) throw new Error('Clasificación manual sin producto en catálogo: ' + id);
  }
  const destinationRows = [['codigo_departamento', 'departamento', 'codigo_destino', 'destino', 'region_organizativa', 'cobertura', 'observaciones']];
  const destinationIds = new Set();
  for (const department of departments) {
    for (const city of department.municipalities) {
      if (destinationIds.has(city.code)) throw new Error('Destino duplicado: ' + city.code);
      destinationIds.add(city.code);
      const region = localCodes.has(city.code) ? 'Local y área cercana' : (departmentRegions[department.code] || 'Otras zonas');
      destinationRows.push([department.code, department.name, city.code, city.name, region, 'por confirmar', 'Región organizativa. No implica tarifa ni cobertura.']);
    }
  }
  for (const filename of ['productos-envio.csv', 'destinos-envio-divipola.csv']) {
    if (fs.existsSync(path.join(root, 'Datos', filename))) {
      throw new Error('La base ya existe y no se sobrescribirá: ' + filename);
    }
  }
  writeNewFile('productos-envio.csv', productRows);
  writeNewFile('destinos-envio-divipola.csv', destinationRows);
}

try {
  main();
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
