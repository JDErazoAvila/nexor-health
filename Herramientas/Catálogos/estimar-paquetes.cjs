'use strict';

const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.join(__dirname, '..', '..');
const profiles = [
  { types: ['Fonendoscopios', 'Otoscopio', 'Tensiómetros', 'Kit de tensiómetros y fonendoscopios', 'Tensiómetros digitales', 'glucometro', 'Balanzas digitales', 'Compresores nebulizadores', 'Kit de órganos y sentidos'], min: 0.3, max: 3, dimensions: '35 x 25 x 20', note: 'Equipo pequeño o kit; la caja depende del modelo y sus accesorios.' },
  { types: ['Medias de compresión', 'Medias de compresión deportivas', 'Panty medias con compresión', 'Medias para diabéticos', 'Fajas', 'Fajas Deportivas', 'Rodillera', 'Pantorrillera deportiva', 'Cabestrillos', 'Manga linfedema', 'Leotardo', 'Corrector de postura', 'Brace'], min: 0.1, max: 1.5, dimensions: '30 x 25 x 12', note: 'Prenda o soporte para una unidad; el volumen depende de talla y presentación.' },
  { types: ['Pulsioxímetros', 'Termómetros digitales', 'Cintas métricas', 'Torniquetes', 'Linternas de diagnóstico', 'Gorros médicos', 'Tijeras', 'Goniómetros', 'Bandas y relojes inteligentes', 'Ejercitador de Dedos', 'Cintas kinesiológicas', 'Martillos', 'Pines', 'Gafas de seguridad', 'Plastilina'], min: 0.1, max: 1, dimensions: '25 x 20 x 12', note: 'Accesorio individual; la presentación puede modificar el paquete.' },
  { types: ['Compresa de terapia', 'Higiene', 'Toma de muestra', 'Sistemas de disección', 'Pad de suturas', 'RCP'], min: 0.2, max: 2, dimensions: '35 x 25 x 15', note: 'Presentación individual supuesta; verificar contenido y materiales.' },
  { types: ['Caminadores estándar', 'Caminadores con ruedas'], min: 3, max: 12, dimensions: '90 x 65 x 25', note: 'Supuesto plegado o desmontado; comprobar embalaje y componentes.' },
  { types: ['Bastones de un apoyo', 'Bastones de cuatro apoyos', 'Muletas convencionales', 'Muletas canadienses'], min: 1, max: 5, dimensions: '120 x 25 x 20', note: 'Dimensiones supuestas para unidades ajustables; confirmar largo de la variante.' },
  { types: ['Cómodos sanitarios', 'Eleva sanitarios', 'Silla Ducha'], min: 2, max: 10, dimensions: '65 x 55 x 35', note: 'Supuesto de embalaje parcial o desmontado; verificar el producto.' },
  { types: ['Pelota de Ejercicio'], min: 0.5, max: 3, dimensions: '35 x 30 x 20', note: 'Supuesto de pelota desinflada; verificar diámetro y presentación.' },
  { types: ['Aspiradores de secreción'], min: 2, max: 8, dimensions: '45 x 40 x 35', note: 'Equipo con accesorios y protección; verificar modelo y contenido.' },
  { types: ['Sillas de ruedas de transporte', 'Sillas de ruedas estándar', 'silla de ruedas activa'], min: 10, max: 35, dimensions: '100 x 80 x 45', note: 'Supuesto plegado o desmontado; algunas variantes pueden superar estos valores. Cotización individual.' }
];

const mappings = new Map();
for (const profile of profiles) {
  for (const type of profile.types) {
    if (mappings.has(type)) {
      // Repeated entries must not be assigned to different package assumptions.
      if (mappings.get(type) !== profile) throw new Error('Tipo duplicado: ' + type);
    }
    mappings.set(type, profile);
  }
}

function cell(value) {
  const text = String(value ?? '');
  return /[;"\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
}

function main() {
  const target = path.join(root, 'Datos', 'estimaciones-paquetes.csv');
  if (fs.existsSync(target)) throw new Error('El archivo ya existe y no se sobrescribirá: ' + target);
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync(path.join(root, 'Assets', 'Js', 'catalogo-productos.js'), 'utf8'), context);
  const products = context.window.NEXOR_PRODUCTS;
  if (!Array.isArray(products) || !products.length) throw new Error('No se pudo leer el catálogo.');
  const ids = new Set();
  const rows = [['id_producto', 'nombre', 'tipo', 'estado', 'peso_min_kg', 'peso_max_kg', 'caja_ejemplo_cm', 'base', 'observaciones']];
  let estimated = 0;
  for (const product of products) {
    if (!product.id || ids.has(product.id)) throw new Error('ID ausente o duplicado: ' + product.id);
    ids.add(product.id);
    const profile = mappings.get(product.productType);
    if (profile) {
      estimated++;
      rows.push([product.id, product.name, product.productType, 'supuesto no verificado', profile.min, profile.max, profile.dimensions, 'Supuesto orientativo por tipo, una unidad; no medido', profile.note]);
    } else {
      rows.push([product.id, product.name, product.productType, 'pendiente de revisión', '', '', '', 'Sin supuesto aplicable', 'Tipo ambiguo o requiere medición y cotización individual.']);
    }
  }
  fs.writeFileSync(target, '\uFEFF' + rows.map(row => row.map(cell).join(';')).join('\n') + '\n', { encoding: 'utf8', flag: 'wx' });
  console.log('Inventario: ' + products.length + '; con supuesto orientativo: ' + estimated + '; pendientes: ' + (products.length - estimated) + '.');
}

try {
  main();
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
