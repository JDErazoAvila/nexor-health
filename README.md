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
| `servicio-*.html` / `servicios.css` | Páginas heredadas del sitio anterior (fuera del menú) |

## Personalización rápida

- **Precios:** busque `class="price"` y `data-price` en `index.html`.
- **Fotos:** copie sus JPG en `productos/` con los nombres indicados en `productos/LEEME.txt`.
- **WhatsApp:** el número de pedidos está en los enlaces `wa.me/573053252358` de `index.html`.

© 2026 NEXOR

