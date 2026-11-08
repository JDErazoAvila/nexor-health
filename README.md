# NEXOR - MEDICAL SYSTEMS

Plataforma web de NEXOR - MEDICAL SYSTEMS, comercializadora colombiana de productos médicos, con catálogo consultable para personas e instituciones y solicitudes de cotización por WhatsApp.

## Características

- Catálogo de 372 productos con precios publicados en COP, categorías, marcas, referencias y variantes.
- Búsqueda por nombre, referencia, marca, categoría, tipo de producto o variante, con filtros y paginación.
- Las fichas muestran las descripciones del catálogo, variantes y precios por variante, disponibilidad e imágenes de producto; las fichas permiten recorrer la galería disponible.
- La lista de cotización conserva productos, variantes y cantidades en el navegador; permite editarlos y preparar un mensaje con nombre, correo, organización y observaciones.
- El mensaje se muestra para revisión antes de abrir WhatsApp. Los datos del formulario no se guardan en el navegador ni se envían automáticamente.
- El pago en línea permanece deshabilitado hasta conectar una pasarela comercial.
- Cada ficha abre una ventana de detalle con la opción de solicitar una cotización.
- Chat guiado para resolver preguntas frecuentes, buscar productos en el catálogo y continuar la consulta por WhatsApp; no requiere servicios externos.
- El producto destacado de la portada cambia automáticamente y permite avanzar o retroceder manualmente; la rotación se pausa al interactuar o al reducir movimiento.
- El formulario prepara una solicitud con organización, producto y cantidad para continuar por WhatsApp.
- La sección institucional explica el proceso de cotización y aclara que disponibilidad, impuestos aplicables, precio final y condiciones de entrega deben confirmarse en cada solicitud.
- Los apartados de privacidad, términos comerciales, entrega, garantías y devoluciones son marcadores pendientes de aprobación; no son políticas publicadas.
- La sección de redes mantiene visibles los banners de Instagram, Facebook y TikTok; sus enlaces oficiales se configuran en `socialProfileUrls` dentro de `index.html` y solo se activan al validar cada URL.
- Guía interactiva de formalización en nueve etapas, con resumen gráfico, fuentes oficiales y centro documental cuyos estados se guardan localmente en el navegador.
- Diseño responsive: catálogo de cinco columnas en pantallas amplias, cuatro en escritorio, dos en móvil y una en teléfonos estrechos.
- Diseño responsive con identidad tecnológica en azul profundo y turquesa, usando las tipografías Orbitron y Manrope.

La lista toma los precios actuales mínimos de `Datos/Catálogos/catalogo-siempre-salud-fuente.xlsx` como precios publicados de NEXOR; si ese mínimo corresponde a una variante agotada, muestra el menor precio entre las variantes disponibles. `Herramientas/Catálogos/generar-catalogo-siempre-salud.ps1` aplica actualmente un descuento del 30 % salvo a Littmann. Confirme que esta regla siga aprobada antes de regenerar o publicar los precios. El sitio no declara si los precios incluyen impuestos ni infiere presentaciones no registradas; impuestos aplicables, disponibilidad, presentación, precio final y entrega se confirman al cotizar. El sitio usa las descripciones e imágenes incluidas en el Excel.

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
| `Guías/ruta-formalizacion.html` | Guía desplegable de formalización empresarial, tributaria, comercial y sanitaria; el estado del centro documental se guarda solo en el navegador local |
| `Guías/ruta-formalizacion-resumen.svg` | Infografía resumen enlazada con la guía interactiva |
| `index.html` | Catálogo, lista de cotización, chat guiado, información institucional, marcadores legales, formulario de contacto y detalles de productos |
| `Assets/Css/site.css` | Identidad visual, diseño responsive, tarjetas y componentes de la interfaz |
| `Assets/Images/fondo-circuitos.svg` | Fondo gráfico del sitio |
| `Assets/Js/catalogo-productos.js` | Catálogo web generado: productos, descripciones, precios, imágenes, categorías, marcas y variantes |
| `Datos/Catálogos/catalogo-siempre-salud-fuente.xlsx` | Fuente de los productos, descripciones, precios, imágenes, categorías y variantes |
| `Herramientas/Catálogos/generar-catalogo-siempre-salud.ps1` | Genera el archivo JavaScript del catálogo desde el Excel |
| `Análisis/Catálogos/` y `Análisis/Precios/` | Cuadernos y resultados de análisis; el cuaderno de comparación es una referencia histórica |
| `Documentos/` | Documentos empresariales clasificados por empresa, planeación, legal, catálogo, finanzas y mercado |
| `Herramientas/Catálogos/` y `Herramientas/Precios/` | Scrapers y calculadora de precios |
| `Herramientas/Scraping-Temu/` | Instalador del scraper Temu; falta el archivo `scraper_temu.py` requerido para ejecutarlo |
| `Logs/Catálogo-GMD/` | Registro conservado del scraper GMD |
| `Respaldos/` | Respaldos locales conservados |
| `Nexor_comparador_precios/` | Comparador de precios independiente, con su propio entorno, informes y configuración |
| `Siempresalud_sync/` | Sincronizador independiente del proveedor Siempre Salud |

## Personalización rápida

- **Productos, descripciones, imágenes, categorías, precios y variantes:** actualice el Excel fuente y ejecute `.\Herramientas\Catálogos\generar-catalogo-siempre-salud.ps1` desde la raíz en PowerShell.
- **Guía de formalización:** abra `Guías/ruta-formalizacion.html`; la versión previa se conserva en `Guías/ruta-formalizacion-anterior.html`.
- **Redes sociales:** agregue la URL oficial de cada perfil en `socialProfileUrls` de `index.html`; el enlace se activará solo si corresponde al dominio de esa red.
- **WhatsApp:** el número de pedidos está en los enlaces `wa.me/573053252358` de `index.html`.
- **Teléfono y correo:** la línea de atención y el correo electrónico se mostrarán como disponibles próximamente; mientras tanto, el canal de contacto activo es WhatsApp.

© 2026 NEXOR - MEDICAL SYSTEMS
