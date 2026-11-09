'use strict';

const fs = require('node:fs');
const path = require('node:path');

async function main() {
  const url = 'https://www.datos.gov.co/resource/gdxc-w37w.json?$limit=5000&$order=cod_mpio';
  const response = await fetch(url);
  if (!response.ok) throw new Error('No se pudo consultar DIVIPOLA: HTTP ' + response.status);
  const rows = await response.json();
  if (!Array.isArray(rows) || rows.length < 1100 || rows.length >= 5000) {
    throw new Error('La fuente DIVIPOLA está vacía, incompleta o excede el límite de descarga.');
  }
  const departments = new Map();
  const municipalityCodes = new Set();
  for (const row of rows) {
    if (!/^\d{2}$/.test(row.cod_dpto) || !/^\d{5}$/.test(row.cod_mpio) ||
        !row.cod_mpio.startsWith(row.cod_dpto) || !row.dpto || !row.nom_mpio ||
        municipalityCodes.has(row.cod_mpio)) {
      throw new Error('Registro DIVIPOLA inválido o duplicado: ' + JSON.stringify(row));
    }
    municipalityCodes.add(row.cod_mpio);
    if (!departments.has(row.cod_dpto)) {
      departments.set(row.cod_dpto, { code: row.cod_dpto, name: row.dpto, municipalities: [] });
    }
    const department = departments.get(row.cod_dpto);
    if (department.name !== row.dpto) throw new Error('Nombre de departamento inconsistente: ' + row.cod_dpto);
    department.municipalities.push({ code: row.cod_mpio, name: row.nom_mpio });
  }
  if (departments.size !== 33) throw new Error('Se esperaban 32 departamentos y Bogotá D. C.');
  const output = [...departments.values()];
  const filename = path.join(__dirname, '..', '..', 'Assets', 'Js', 'municipios-colombia.js');
  fs.writeFileSync(filename, 'window.NEXOR_LOCATIONS = ' + JSON.stringify(output) + ';\n', 'utf8');
  console.log('DIVIPOLA: ' + rows.length + ' localidades y ' + departments.size + ' departamentos y distritos.');
}

main().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
