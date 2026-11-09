# NEXOR - MEDICAL SYSTEMS

Plataforma web de NEXOR - MEDICAL SYSTEMS, comercializadora colombiana de productos médicos, con catálogo consultable para personas e instituciones y solicitudes de cotización por WhatsApp.

## Características

- Catálogo de 372 productos con precios publicados en COP, categorías, marcas, referencias y variantes.
- Búsqueda por nombre, referencia, marca, categoría, tipo de producto o variante, con filtros y paginación.
- Las fichas muestran las descripciones del catálogo, variantes y precios por variante, disponibilidad e imágenes de producto; las fichas permiten recorrer la galería disponible.
- El carrito conserva productos, variantes y cantidades en el navegador, sincroniza precios y disponibilidad con el catálogo y sugiere productos de la misma categoría disponibles.
- El carrito organiza la compra en etapas de productos, entrega y resumen, con una ventana ampliada en pantallas grandes para entrega y pago. El resumen muestra los datos de contacto y entrega ingresados y permite editarlos; también permite explorar ejemplos visuales de medios de pago y bancos. El pago en línea permanece desactivado porque Wompi aún no está integrado. No crea pedidos ni cobra y los datos de contacto y entrega no se envían ni guardan en el navegador. Algunas rutas muestran una referencia de envío orientativa; impuestos y total final quedan por confirmar.
- Cada ficha abre una ventana de detalle con la opción de solicitar una cotización.
- Chat guiado para resolver preguntas frecuentes, buscar productos en el catálogo y continuar la consulta por WhatsApp; no requiere servicios externos.
- Conexión futura para un asistente comercial con IA: preparada en el cliente, desactivada por defecto y sin proveedor ni servidor integrados. El chat guiado actual sigue funcionando sin IA.
- El producto destacado de la portada cambia automáticamente y permite avanzar o retroceder manualmente; la rotación se pausa al interactuar o al reducir movimiento.
- El formulario prepara una solicitud con organización, producto y cantidad para continuar por WhatsApp.
- Los selectores de entrega usan departamentos y municipios de Colombia. El carrito muestra una referencia de envío y un total orientativo solo para rutas y productos elegibles; no son tarifas garantizadas ni incluyen impuestos pendientes. La presencia de un municipio no garantiza cobertura.
- La sección institucional explica el proceso de cotización y aclara que disponibilidad, impuestos aplicables, precio final y condiciones de entrega deben confirmarse en cada solicitud.
- Los apartados de privacidad, términos comerciales, entrega, garantías y devoluciones son marcadores pendientes de aprobación; no son políticas publicadas.
- La sección de redes mantiene visibles los banners de Instagram, Facebook y TikTok; sus enlaces oficiales se configuran en `socialProfileUrls` dentro de `index.html` y solo se activan al validar cada URL.
- Guía interactiva de formalización en nueve etapas, con resumen gráfico, fuentes oficiales y centro documental cuyos estados se guardan localmente en el navegador.
- Diseño responsive: catálogo de cinco columnas en pantallas amplias, cuatro en escritorio, dos en móvil y una en teléfonos estrechos.
- Diseño responsive con identidad tecnológica en azul profundo y turquesa, usando las tipografías Orbitron y Manrope.

La lista toma los precios actuales mínimos de `Datos/Catálogos/catalogo-siempre-salud-fuente.xlsx` como precios publicados de NEXOR; si ese mínimo corresponde a una variante agotada, muestra el menor precio entre las variantes disponibles. `Herramientas/Catálogos/generar-catalogo-siempre-salud.ps1` aplica actualmente un descuento del 30 % salvo a Littmann. Confirme que esta regla siga aprobada antes de regenerar o publicar los precios. El sitio no declara si los precios incluyen impuestos ni infiere presentaciones no registradas; impuestos aplicables, disponibilidad, presentación, precio final y entrega se confirman al cotizar. El sitio usa las imágenes incluidas en el Excel.

### Vista de prueba de compra

Para ver el carrito de demostración, abra `index.html?checkout=prueba` en el servidor local; retire el parámetro para volver al flujo normal. La vista usa una clave de carrito independiente, muestra avisos de prueba y permite recorrer contacto, entrega, resumen y selección de pago sin conectarse a una pasarela, crear un pedido ni enviar los datos del formulario. Use únicamente datos ficticios. El envío fijo de $15.000 COP es inventado para la demostración, no es una tarifa ni confirma cobertura. El total suma los precios de catálogo y ese envío ficticio, sin calcular impuestos no verificados; no es una oferta ni total real. Simular el pago solo muestra una confirmación de simulación. En la página normal el pago está deshabilitado y no se emplea la tarifa ficticia.

### Referencias orientativas de envío

Para una sola unidad disponible, el carrito muestra la referencia del destino solo si existe una cotización con tarifa para el escenario hipotético de Cali, 1 kg, caja de 50 × 38 × 42 cm, valor declarado de $100.000 y entrega en dirección. La fecha es 9 de noviembre de 2026. El total orientativo suma subtotal y referencia, sin calcular impuestos pendientes. No es tarifa ni total definitivo: el producto, valor declarado y paquete reales pueden ser distintos. Múltiples unidades, destinos sin datos y productos sin supuesto compatible quedan por confirmar.

Como filtro conservador, el supuesto no verificado de una unidad debe tener peso mínimo de hasta 1 kg y caja de ejemplo que quepa en las dimensiones del paquete hipotético; esto **no prueba** que el producto pese 1 kg, que la caja real quepa o que la tarifa aplique. Productos voluminosos y sin perfil quedan excluidos. `Herramientas/Catálogos/actualizar-referencias-envio.ps1` genera `Assets/Js/referencias-envio.js` desde los CSV existentes; concilie las rutas y supuestos al actualizarlos. La referencia específica del kit a Bogotá no se mezcla con este escenario, pues sus condiciones son incompletas. La vista `?checkout=prueba` mantiene su envío ficticio independiente. No habilitar pagos reales con estas referencias.

Algunas descripciones cuentan con una versión editorial en `Datos/Catálogos/descripciones-editadas.json`. El generador utiliza esa versión para los identificadores indicados y la descripción del Excel para los demás productos. Revise las versiones editoriales si cambia la información de esos productos en la fuente.

### Preparación del asistente comercial con IA

`Assets/Js/asistente-ia.js` contiene un adaptador de cliente desactivado; no hace llamadas mientras `enabled` sea `false`. No hay proveedor, credenciales, backend ni respuestas de IA conectados. El chat actual sigue siendo guiado. Esta preparación no está lista para producción ni debe activarse cambiando solo la bandera.

Antes de activar, seleccionar proveedor y alojamiento, revisar sus costos y tratamiento de datos, aprobar la política y el aviso de privacidad específicos, e identificar el proveedor y la finalidad en el aviso de consentimiento. El usuario debe aceptar antes de enviar cada consulta; no solicitar datos clínicos ni personales. El aviso actual es un marcador para la futura integración, no una política aprobada. No registrar consultas ni datos personales en logs sin una política y base aplicable. Evaluar protección de datos y requisitos legales con asesoría.

El backend pendiente debe servir en el mismo origen, con HTTPS (HTTP solo para pruebas locales), guardar las credenciales exclusivamente en el servidor y aplicar controles de acceso, límites de frecuencia, tamaño y costo, gestión segura de errores y protección contra abusos. Para GitHub Pages se necesita configurar un servidor o proxy en el mismo origen o adaptar de forma segura la arquitectura; Pages por sí solo no ejecuta el backend.

Contrato previsto: `POST /api/asistente` recibe JSON `{ "question": "..." }` (máximo 180 caracteres) y devuelve `{ "answer": "...", "productIds": ["id-del-catalogo"] }`; máximo tres identificadores y 3.000 caracteres en la respuesta. Los identificadores se resuelven contra el catálogo local y las respuestas se muestran como texto, no HTML. Los errores HTTP o respuestas inválidas se muestran como fallos; no se simula una respuesta de IA. El cliente no envía automáticamente el historial ni los datos del carrito. Los botones rápidos continúan usando el chat guiado local.

El servicio deberá consultar únicamente datos comerciales autorizados y vigentes del catálogo, tratar mensajes y contenido de producto como datos no confiables, manejar instrucciones maliciosas, probar preguntas clínicas y rechazar diagnóstico o tratamiento. No debe inventar referencias, características, disponibilidad confirmada, impuestos, tarifas, pagos o pedidos. Las salvaguardas requieren pruebas y supervisión; un mensaje de sistema por sí solo no garantiza respuestas correctas. Mantener revisión humana para información no confirmada.

Para comprobar el adaptador sin credenciales ni llamadas externas: `node --test .\Herramientas\IA\asistente-ia.test.cjs`.

Para habilitar pagos con Wompi será necesario activar una cuenta comercial, definir cómo obtener el total final y el envío, e implementar un servicio seguro que valide precios y disponibilidad, genere la firma de integridad sin exponer el secreto y confirme el estado mediante los mecanismos oficiales de Wompi. Primero deben realizarse pruebas en el entorno de pruebas; no se deben incluir secretos ni credenciales privadas en el sitio estático. El resumen actual no inicia transacciones.

La selección de medios y bancos de ejemplo en el resumen normal es solo una demostración visual: la lista de bancos es parcial, no recoge datos de pago ni inicia transacciones y no acredita que esos medios estén disponibles. Sustituirla por el flujo oficial de Wompi y los medios/bancos realmente habilitados para la cuenta; no reutilizar los valores de ejemplo al procesar pagos. No añadir formularios propios para claves o datos de tarjeta sin el diseño seguro y los requisitos de cumplimiento correspondientes.

`Herramientas/Pagos/wompi-checkout.cjs` prepara, exclusivamente en Node.js, una URL del checkout oficial firmada con un importe en centavos y una referencia proporcionados por el servidor. Valida formato y coherencia de credenciales de Sandbox o producción; no crea pedidos, no consulta disponibilidad, no calcula ni valida el total, no procesa pagos y no verifica transacciones. No es un servidor ni está conectado al carrito. No exponer esta función ni el secreto al navegador ni firmar importes proporcionados por el cliente. La referencia única debe crearse y reservarse de forma persistente en el servidor.

Para integrarla realmente, el servidor deberá validar las líneas y variantes contra fuentes autorizadas, impuestos y tarifa de envío real; obtener aceptación del importe definitivo, persistir una orden y una referencia única, y solo entonces crear el checkout firmado. Debe proteger datos personales y puntos de acceso, aplicar controles contra abuso e idempotencia, verificar eventos de Wompi y consultar el estado, monto, moneda y referencia por el canal oficial antes de marcar una orden como pagada. Una redirección no prueba un pago. Definir alojamiento seguro, aviso y política de privacidad aplicables y procedimientos de reconciliación y devolución; probar primero en Sandbox. El listado de bancos y medios disponibles lo gestiona la experiencia oficial y depende de la cuenta y configuración; no se puede garantizar «todos» sin verificar con Wompi.

Pruebas locales sin credenciales ni red: `node --test .\Herramientas\Pagos\wompi-checkout.test.cjs .\Herramientas\Pagos\wompi-sandbox.test.cjs`.

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
| `Datos/tarifas-envio-referencia.csv` | Cotizaciones orientativas con sus supuestos; el escenario hipotético alimenta referencias del carrito, no tarifas garantizadas |
| `Datos/regiones-envio.csv` | Organización de destinos consultados por región y departamento; la región no implica una tarifa compartida |
| `Datos/clasificacion-envios.json` | Grupos orientativos de paquetes y clasificaciones provisionales por identificador de producto |
| `Datos/productos-envio.csv` | Inventario inicial de productos y clasificación orientativa; peso y dimensiones empacadas pendientes |
| `Datos/estimaciones-paquetes.csv` | Suposiciones sin validar de peso y caja por tipo, usadas únicamente para filtrar referencias orientativas |
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
- **Referencias de envío:** registre cada cotización con origen, destino, fecha y características del paquete en `Datos/tarifas-envio-referencia.csv`, y asigne el destino a una región en `Datos/regiones-envio.csv`. Las regiones solo organizan las ciudades: no se extrapolan tarifas. En `Datos/clasificacion-envios.json`, clasifique productos por identificador después de confirmar el peso y las dimensiones empacadas; los productos no registrados y las clasificaciones provisionales requieren cotización individual. El ejemplo de 1 kg y valor declarado de $100.000 es hipotético y se muestra solo como referencia, según el filtro descrito arriba; no es la tarifa del producto real. Los envíos desde El Placer requieren confirmar con la transportadora el municipio de origen. Estos archivos forman parte del repositorio y no deben considerarse privados si el repositorio o sitio publicado son públicos.
- **Inventario inicial de envíos:** `Datos/productos-envio.csv` reúne los identificadores del catálogo y sugerencias provisionales por tipo; no son medidas ni garantía de embalaje. Complete peso y dimensiones empacadas, fuente y estado después de verificarlos; revise cada variante y las cantidades combinadas. `Datos/destinos-envio-divipola.csv` organiza destinos por código DIVIPOLA y región, sin inferir cobertura ni precio. Los destinos no relacionados con una cotización en `Datos/tarifas-envio-referencia.csv` siguen pendientes. Ambos son inventarios iniciales independientes de la tienda y no activan cálculos. `node .\Herramientas\Catálogos\crear-base-envios.cjs` crea las bases solo si no existen, para no sobrescribir mediciones manuales; al cambiar el catálogo o DIVIPOLA deben conciliarse los registros sin borrar datos verificados.
- **Estimaciones de paquetes:** `Datos/estimaciones-paquetes.csv` contiene hipótesis orientativas para una unidad según su tipo: rango de peso empacado y una caja de ejemplo expresada como largo × ancho × alto en centímetros. Son estimaciones sin medición ni fuentes por producto; no garantizan que el producto quepa ni que su peso esté dentro del rango. Tipos ambiguos, equipos motorizados y otros productos sin perfil quedan pendientes. Se usan para filtrar referencias orientativas, nunca para cobrar; confirme cada variante, embalaje, peso real y volumétrico con el proveedor y la transportadora. El inventario se genera una sola vez con `node .\Herramientas\Catálogos\estimar-paquetes.cjs` y no sobrescribe un archivo existente.
- **Guía de formalización:** abra `Guías/ruta-formalizacion.html`; la versión previa se conserva en `Guías/ruta-formalizacion-anterior.html`.
- **Redes sociales:** agregue la URL oficial de cada perfil en `socialProfileUrls` de `index.html`; el enlace se activará solo si corresponde al dominio de esa red.
- **WhatsApp:** el número de pedidos está en los enlaces `wa.me/573053252358` de `index.html`.
- **Teléfono y correo:** la línea de atención y el correo electrónico se mostrarán como disponibles próximamente; mientras tanto, el canal de contacto activo es WhatsApp.

© 2026 NEXOR - MEDICAL SYSTEMS
