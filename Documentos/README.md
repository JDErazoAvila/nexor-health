# NEXOR - MEDICAL SYSTEMS

Plataforma web de productos y equipos médicos para instituciones de salud, con búsqueda, fichas de producto, precios en COP y solicitud de cotización por WhatsApp.

## Características

- Catálogo de 253 productos con precios publicados en COP, categorías, marcas, referencias y variantes.
- Búsqueda por nombre, referencia, marca, categoría, tipo de producto o variante, con filtros y paginación.
- Las fichas muestran las descripciones del catálogo, variantes y precios por variante, disponibilidad e imágenes de producto; las fichas permiten recorrer la galería disponible.
- El carrito conserva productos, variantes y cantidades en el navegador; permite editar y consultar el pedido por WhatsApp.
- El pago en línea permanece deshabilitado hasta conectar una pasarela comercial.
- Cada ficha abre una ventana de detalle con la opción de solicitar una cotización.
- Chat guiado para resolver preguntas frecuentes, buscar productos en el catálogo y continuar la consulta por WhatsApp; no requiere servicios externos.
- El producto destacado de la portada cambia automáticamente y permite avanzar o retroceder manualmente; la rotación se pausa al interactuar o al reducir movimiento.
- El formulario prepara una solicitud con organización, producto y cantidad para continuar por WhatsApp.
- La sección de redes muestra banners para Instagram, Facebook y TikTok; sus enlaces oficiales se configuran en `socialProfileUrls` dentro de `index.html`.
- Diseño responsive: catálogo de cinco columnas en pantallas amplias, cuatro en escritorio, dos en móvil y una en teléfonos estrechos.
- Diseño responsive con identidad tecnológica en azul profundo y turquesa, usando las tipografías Orbitron y Manrope.

La lista toma los precios actuales mínimos de `siempresalud_catalogo_completo.xlsx` como precios publicados de NEXOR; si ese mínimo corresponde a una variante agotada, muestra el menor precio entre las variantes disponibles. Confirme precios y disponibilidad antes de procesar cada cotización. El sitio usa las descripciones e imágenes autorizadas incluidas en el Excel.

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
| `index.html` | Catálogo, carrito, chat guiado, banners de redes, proceso de cotización, formulario de contacto y detalles de productos |
| `nexor-premium.css` | Identidad visual, diseño responsive, tarjetas y componentes de la interfaz |
| `productos_siempresalud_catalogo.js` | Catálogo web generado: productos, descripciones, precios, imágenes, categorías, marcas y variantes |
| `siempresalud_catalogo_completo.xlsx` | Fuente de los productos, descripciones, precios, imágenes, categorías y variantes |
| `generar_catalogo_siempresalud.ps1` | Genera el archivo JavaScript del catálogo desde el Excel |

## Personalización rápida

- **Productos, descripciones, imágenes, categorías, precios y variantes:** actualice el Excel fuente y ejecute `.\generar_catalogo_siempresalud.ps1` en PowerShell.
- **Redes sociales:** agregue la URL oficial de cada perfil en `socialProfileUrls` de `index.html`; el enlace se activará solo si corresponde al dominio de esa red.
- **WhatsApp:** el número de pedidos está en los enlaces `wa.me/573053252358` de `index.html`.
- **Teléfono y correo:** la línea de atención y el correo electrónico se mostrarán como disponibles próximamente; mientras tanto, el canal de contacto activo es WhatsApp.

© 2026 NEXOR - MEDICAL SYSTEMS
