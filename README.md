# NEXOR — Suministros médicos de un solo uso

Catálogo web para la venta de suministros médicos desechables: guantes, mascarillas, jeringas, gasas, batas y más — con carrito de compras y pedido directo por WhatsApp.

## Características

- Catálogo de 10 productos con precios de referencia y ficha visual (icono o foto).
- Carrito de compras con cantidades, total en COP y persistencia local (`localStorage`).
- El pedido se arma automáticamente y se envía por WhatsApp.
- Ilustraciones SVG por producto: coloque sus fotos reales (JPG) en `productos/` y la página las usará automáticamente.
- Sección "Cómo comprar" en 4 pasos y formulario de cotización.
- Diseño responsive con paleta clínica: azul hospitalario, verde médico y cian.

## Vista previa local

Abra `index.html` en su navegador o sirva la carpeta con un servidor local:

```bash
python -m http.server 8000
```

## Publicación en GitHub Pages

1. En el repositorio: **Settings → Pages**.
2. **Source:** `Deploy from a branch`.
3. **Branch:** `main` y carpeta `/ (root)` → **Save**.
4. El sitio quedará disponible en `https://TU_USUARIO.github.io/nexor-health/`.

## Estructura del proyecto

| Ruta | Contenido |
|---|---|
| `index.html` | Catálogo, cómo comprar, carrito y contacto |
| `productos/` | Imágenes de producto (SVG de referencia + `LEEME.txt` con los nombres esperados para fotos JPG) |

## Personalización rápida

- **Precios:** busque `class="price"` y `data-price` en `index.html`.
- **Fotos:** copie sus JPG en `productos/` con los nombres indicados en `productos/LEEME.txt`.
- **WhatsApp:** el número de pedidos está en los enlaces `wa.me/573053252358` de `index.html`.

## Actualizar precios desde Temu (script de web scraping)

En `scraper_temu.py` hay un script que abre Temu Colombia en un navegador real
(Playwright), busca cada uno de los 10 productos del catálogo y extrae
título + precio en COP a un JSON/CSV.

### En Windows (PowerShell)

1. **Instala Python** (una sola vez) si no lo tienes:
   `winget install --id Python.Python.3.12 -e --source winget`

2. **Instalación automática** (pip, playwright y Chromium):
   `powershell -ExecutionPolicy Bypass -File instalar-temu.ps1 -SoloInstalar`

3. **Corre el scraper** (los 10 productos):
   `powershell -ExecutionPolicy Bypass -File instalar-temu.ps1`

Opciones:
- `... -Consulta "guantes nitrilo 100"` — una sola búsqueda libre
- `python scraper_temu.py --headless` — sin ventana (suele chocar con el captcha de Temu)

Salidas: `precios_temu_AAAAMMDD_HHMMSS.json`, `.csv` y carpeta `raw/` con el HTML de cada búsqueda.
Los precios extraídos se usan luego para recalcular `index.html` (costo Temu + 20 %).

> Nota: Temu bloquea accesos automatizados con captchas; por eso el script usa un
> navegador real y espera a que completes la verificación manualmente la primera vez.
> Si prefieres no instalar nada, la vía manual (Temu en modo incógnito + calcular-precios.html) es la más rápida.

## Herramienta local de cálculo

`calcular-precios.html` (ábrela con doble clic en el navegador) permite ingresar
el costo visto en Temu por cada producto y calcula el precio NEXOR (costo × 1,20),
mostrando además el `data-price` listo para pegar en `index.html`.

© 2026 NEXOR

