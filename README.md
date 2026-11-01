# NEXOR - MEDICAL SYSTEMS

Plataforma web de productos y equipos médicos para instituciones de salud, con fichas, imágenes disponibles, precios 2026 y solicitud de cotización por WhatsApp.

## Características

- Catálogo consolidado 2026 de 243 productos, con precios publicados en COP (IVA incluido), categorías, búsqueda y paginación.
- Cada ficha abre una ventana de detalle con la imagen disponible y la opción de solicitar una cotización.
- Las fichas incluyen especificaciones y disponibilidad cuando están indicadas en el catálogo fuente.
- Búsqueda por nombre, referencia, categoría o especificaciones, filtros y orden de productos.
- El formulario prepara una solicitud con organización, producto y cantidad para continuar por WhatsApp.
- Diseño responsive con identidad tecnológica en azul profundo y turquesa, usando las tipografías Orbitron y Manrope.

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
| `index.html` | Catálogo, proceso de cotización, formulario de contacto y detalles de productos |
| `nexor-premium.css` | Identidad visual, diseño responsive, tarjetas y componentes de la interfaz |
| `productos_gmd_catalogo.js` | Productos, precios 2026, referencias, categorías, especificaciones e imágenes |
| `Catalogo_consolidado_precios_2026.xlsx` | Fuente del catálogo consolidado y los precios publicados |
| `productos_gmd_catalogo_completo.csv` | Catálogo CSV complementario |

## Personalización rápida

- **Productos, categorías, precios e imágenes:** actualice `productos_gmd_catalogo.js` usando la hoja consolidada del archivo Excel.
- **WhatsApp:** el número de pedidos está en los enlaces `wa.me/573053252358` de `index.html`.

© 2026 NEXOR - MEDICAL SYSTEMS
