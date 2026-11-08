# NEXOR - Comparador de precios GMD

## Instalación (Windows)

1. Instala Python 3.11 o superior.
2. Descomprime esta carpeta.
3. Abre PowerShell dentro de la carpeta.
4. Ejecuta:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

5. Pega los SKU, uno por línea, en `sku_gmd.txt`.
6. Si quieres modificar los sitios, edita `competidores.txt`.
7. Ejecuta:

```powershell
py main.py
```

Los informes se guardan en `Reports/`, los registros en `Logs/` y los puntos de control en `Checkpoints/`.

## Alcance y limitaciones

- El programa consulta páginas públicas encontradas en los sitemap XML de cada dominio.
- Si no encuentra sitemap, prueba un conjunto pequeño de enlaces de producto en la página principal.
- Sólo registra precio cuando lo puede leer de datos estructurados (JSON-LD) o metadatos de producto.
- Compara SKU exactos. No etiqueta productos parecidos como equivalentes.
- No inicia sesión, no evade CAPTCHA, bloqueos, robots.txt ni restricciones técnicas.
- No todos los sitios publican SKU, precio o catálogo en sus páginas públicas.
- Un resultado vacío significa que no se pudo verificar en esta ejecución; no demuestra inexistencia.
- El campo de disponibilidad es una señal publicada por la página, no una confirmación de inventario físico.
- Antes de automatizar consultas recurrentes, verifica las condiciones de uso de cada proveedor y solicita autorización cuando corresponda.

## Nota

Este es un primer scraper genérico de descubrimiento. Algunos sitios requerirán adaptadores específicos según su plataforma (Shopify, WooCommerce u otra) y estructura real. No se deben asumir endpoints privados ni inventario mayorista.
