# NEXOR - MEDICAL SYSTEMS

Plataforma web de NEXOR - MEDICAL SYSTEMS, comercializadora colombiana de productos médicos, con catálogo consultable para personas e instituciones y solicitudes de cotización por WhatsApp.

## Características

- Catálogo de 372 productos con precios publicados en COP, categorías, marcas, referencias y variantes.
- Búsqueda por nombre, referencia, marca, categoría, tipo de producto o variante, con filtros y paginación.
- Las fichas muestran las descripciones del catálogo, variantes y precios por variante, disponibilidad e imágenes de producto; las fichas permiten recorrer la galería disponible.
- La lista de cotización conserva productos, variantes y cantidades en el navegador; permite editarlos y preparar un mensaje con nombre, correo, organización y observaciones.
- El mensaje se muestra para revisión antes de abrir WhatsApp. Los datos del formulario no se guardan en el navegador ni se envían automáticamente.
- El carrito permite recorrer una demostración de entrega, resumen y pago sin crear pedidos ni realizar cobros. La ciudad y el departamento no se guardan ni se envían; el envío y el total final quedan por confirmar. El pago en línea permanece deshabilitado; Wompi es la pasarela prevista, pero aún no está integrada ni configurada.
- Cada ficha abre una ventana de detalle con la opción de solicitar una cotización.
- Chat guiado para resolver preguntas frecuentes, buscar productos en el catálogo y continuar la consulta por WhatsApp; no requiere servicios externos.
- El producto destacado de la portada cambia automáticamente y permite avanzar o retroceder manualmente; la rotación se pausa al interactuar o al reducir movimiento.
- El formulario prepara una solicitud con organización, producto y cantidad para continuar por WhatsApp.
- Los selectores de entrega del carrito y del formulario usan departamentos y municipios de Colombia; el envío sigue por cotizar y no se suma al total del carrito. La presencia de un municipio no garantiza cobertura.
- La sección institucional explica el proceso de cotización y aclara que disponibilidad, impuestos aplicables, precio final y condiciones de entrega deben confirmarse en cada solicitud.
- Los apartados de privacidad, términos comerciales, entrega, garantías y devoluciones son marcadores pendientes de aprobación; no son políticas publicadas.
- La sección de redes mantiene visibles los banners de Instagram, Facebook y TikTok; sus enlaces oficiales se configuran en `socialProfileUrls` dentro de `index.html` y solo se activan al validar cada URL.
- Guía interactiva de formalización en nueve etapas, con resumen gráfico, fuentes oficiales y centro documental cuyos estados se guardan localmente en el navegador.
- Diseño responsive: catálogo de cinco columnas en pantallas amplias, cuatro en escritorio, dos en móvil y una en teléfonos estrechos.
- Diseño responsive con identidad tecnológica en azul profundo y turquesa, usando las tipografías Orbitron y Manrope.

La lista toma los precios actuales mínimos de `Datos/Catálogos/catalogo-siempre-salud-fuente.xlsx` como precios publicados de NEXOR; si ese mínimo corresponde a una variante agotada, muestra el menor precio entre las variantes disponibles. `Herramientas/Catálogos/generar-catalogo-siempre-salud.ps1` aplica actualmente un descuento del 30 % salvo a Littmann. Confirme que esta regla siga aprobada antes de regenerar o publicar los precios. El sitio no declara si los precios incluyen impuestos ni infiere presentaciones no registradas; impuestos aplicables, disponibilidad, presentación, precio final y entrega se confirman al cotizar. El sitio usa las imágenes incluidas en el Excel.

Algunas descripciones cuentan con una versión editorial en `Datos/Catálogos/descripciones-editadas.json`. El generador utiliza esa versión para los identificadores indicados y la descripción del Excel para los demás productos. Revise las versiones editoriales si cambia la información de esos productos en la fuente.

Para habilitar pagos con Wompi será necesario activar una cuenta comercial, definir cómo obtener el total final y el envío, e implementar un servicio seguro que valide precios y disponibilidad, genere la firma de integridad sin exponer el secreto y confirme el estado mediante los mecanismos oficiales de Wompi. Primero deben realizarse pruebas en el entorno de pruebas; no se deben incluir secretos ni credenciales privadas en el sitio estático. El resumen actual no inicia transacciones.

### Prueba local de Wompi Sandbox

`Herramientas/Pagos/wompi-sandbox.cjs` prepara un enlace de checkout para una transacción ficticia fija de $1.000 COP. Solo acepta llaves y secreto de integridad **de prueba**; no usa el carrito, no calcula envíos, no crea pedidos y no confirma pagos. No es un servidor ni una integración de producción. Abrir el enlace y completar el checkout requiere una cuenta de Wompi con credenciales Sandbox.

Cuando estén disponibles, configure temporalmente en PowerShell las variables `WOMPI_SANDBOX_PUBLIC_KEY` y `WOMPI_SANDBOX_INTEGRITY_SECRET` con los valores de prueba desde el panel de Wompi y ejecute en la misma ventana:

```powershell
node .\Herramientas\Pagos\wompi-sandbox.cjs
```

La herramienta muestra un enlace que se puede abrir para probar el checkout. Use exclusivamente datos de prueba de Wompi y verifique el resultado en su panel. No comparta ni registre el enlace o los secretos; quite las variables de esa ventana al terminar con `Remove-Item Env:\WOMPI_SANDBOX_PUBLIC_KEY, Env:\WOMPI_SANDBOX_INTEGRITY_SECRET`. Para comprobar la lógica local sin credenciales: `node --test .\Herramientas\Pagos\wompi-sandbox.test.cjs`. Consulte la [documentación oficial de Wompi](https://docs.wompi.co/docs/colombia/widget-checkout-web/) antes de la integración real.

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
| `Assets/Js/municipios-colombia.js` | Lista local de DIVIPOLA para los selectores de entrega |
| `Datos/Catálogos/catalogo-siempre-salud-fuente.xlsx` | Fuente de los productos, descripciones, precios, imágenes, categorías y variantes |
| `Datos/Catálogos/descripciones-editadas.json` | Descripciones editoriales seleccionadas, asociadas a identificadores de producto |
| `Datos/tarifas-envio-referencia.csv` | Cotizaciones orientativas internas, con sus supuestos; no alimentan el carrito ni sustituyen la cotización del envío real |
| `Datos/regiones-envio.csv` | Organización de destinos consultados por región y departamento; la región no implica una tarifa compartida |
| `Datos/clasificacion-envios.json` | Grupos orientativos de paquetes y clasificaciones provisionales por identificador de producto |
| `Datos/productos-envio.csv` | Inventario inicial de productos y clasificación orientativa; peso y dimensiones empacadas pendientes |
| `Datos/destinos-envio-divipola.csv` | Destinos DIVIPOLA agrupados para organización interna, con cobertura por confirmar |
| `Herramientas/Catálogos/generar-catalogo-siempre-salud.ps1` | Genera el archivo JavaScript del catálogo desde el Excel |
| `Análisis/Catálogos/` y `Análisis/Precios/` | Cuadernos y resultados de análisis; el cuaderno de comparación es una referencia histórica |
| `Documentos/` | Documentos empresariales clasificados por empresa, planeación, legal, catálogo, finanzas y mercado |
| `Herramientas/Catálogos/` y `Herramientas/Precios/` | Scrapers y calculadora de precios |
| `Herramientas/Pagos/` | Herramienta local aislada y pruebas para generar un enlace ficticio de Wompi Sandbox |
| `Herramientas/Scraping-Temu/` | Instalador del scraper Temu; falta el archivo `scraper_temu.py` requerido para ejecutarlo |
| `Logs/Catálogo-GMD/` | Registro conservado del scraper GMD |
| `Respaldos/` | Respaldos locales conservados |
| `Nexor_comparador_precios/` | Comparador de precios independiente, con su propio entorno, informes y configuración |
| `Siempresalud_sync/` | Sincronizador independiente del proveedor Siempre Salud |

## Personalización rápida

- **Productos, descripciones, imágenes, categorías, precios y variantes:** actualice el Excel fuente y ejecute `.\Herramientas\Catálogos\generar-catalogo-siempre-salud.ps1` desde la raíz en PowerShell. Para productos con descripción editorial, actualice también `Datos/Catálogos/descripciones-editadas.json`.
- **Municipios:** la lista local proviene de [DIVIPOLA - Códigos municipios, DANE](https://www.datos.gov.co/Mapas-Nacionales/DIVIPOLA-C-digos-municipios/gdxc-w37w), con corte de la fuente al 30 de diciembre de 2024, licencia [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Incluye áreas no municipalizadas e isla; la clasificación no garantiza cobertura de una transportadora. Para actualizarla, ejecute `node .\Herramientas\Catálogos\actualizar-municipios.cjs` y revise la fecha y licencia de la fuente antes de publicar.
- **Referencias de envío:** registre cada cotización con origen, destino, fecha y características del paquete en `Datos/tarifas-envio-referencia.csv`, y asigne el destino a una región en `Datos/regiones-envio.csv`. Las regiones solo organizan las ciudades: no se extrapolan tarifas. En `Datos/clasificacion-envios.json`, clasifique productos por identificador después de confirmar el peso y las dimensiones empacadas; los productos no registrados y las clasificaciones provisionales requieren cotización individual. El ejemplo de 1 kg y valor declarado de $100.000 es hipotético y no se aplica automáticamente a los productos. Los envíos desde El Placer requieren confirmar con la transportadora el municipio de origen. Estos archivos forman parte del repositorio y no deben considerarse privados si el repositorio o sitio publicado son públicos.
- **Inventario inicial de envíos:** `Datos/productos-envio.csv` reúne los identificadores del catálogo y sugerencias provisionales por tipo; no son medidas ni garantía de embalaje. Complete peso y dimensiones empacadas, fuente y estado después de verificarlos; revise cada variante y las cantidades combinadas. `Datos/destinos-envio-divipola.csv` organiza destinos por código DIVIPOLA y región, sin inferir cobertura ni precio. Los destinos no relacionados con una cotización en `Datos/tarifas-envio-referencia.csv` siguen pendientes. Ambos son inventarios iniciales independientes de la tienda y no activan cálculos. `node .\Herramientas\Catálogos\crear-base-envios.cjs` crea las bases solo si no existen, para no sobrescribir mediciones manuales; al cambiar el catálogo o DIVIPOLA deben conciliarse los registros sin borrar datos verificados.
- **Guía de formalización:** abra `Guías/ruta-formalizacion.html`; la versión previa se conserva en `Guías/ruta-formalizacion-anterior.html`.
- **Redes sociales:** agregue la URL oficial de cada perfil en `socialProfileUrls` de `index.html`; el enlace se activará solo si corresponde al dominio de esa red.
- **WhatsApp:** el número de pedidos está en los enlaces `wa.me/573053252358` de `index.html`.
- **Teléfono y correo:** la línea de atención y el correo electrónico se mostrarán como disponibles próximamente; mientras tanto, el canal de contacto activo es WhatsApp.

© 2026 NEXOR - MEDICAL SYSTEMS
