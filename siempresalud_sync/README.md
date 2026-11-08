# Sincronización persistente de Siempre Salud para NEXOR

Este servicio es independiente del navegador. Mantiene una base SQLite para el catálogo **del proveedor**, consulta el catálogo oficial UCP anunciado por `https://siempresalud.co/.well-known/ucp`, guarda el historial y ofrece un panel HTTP protegido. No modifica `Assets/Js/catalogo-productos.js`, precios de venta, márgenes ni inventario propio.

## Fuente y límites verificados

- Siempre Salud publica su plataforma Shopify, su sitemap y sus instrucciones de agente en `https://siempresalud.co/robots.txt` y `https://siempresalud.co/agents.md`.
- El perfil UCP observado anuncia `search_catalog` y `lookup_catalog`; este módulo usa únicamente `search_catalog` para lecturas.
- Shopify exige identificar las llamadas programadas servidor-a-servidor. El cliente firma cada solicitud con HTTP Message Signatures (ECDSA P-256) y forma dual UCP/Web Bot Auth; no intenta sortear autenticación, CAPTCHA, errores 429 ni bloqueos.
- El esquema UCP publica precios, SKU opcional, disponibilidad (`available`/`status`), descripciones, medios, URL, opciones y variantes. **No declara cantidad exacta en inventario**; `supplier_quantity` se guarda siempre como `NULL`.
- El modelo estándar UCP no incluye una propiedad de marca; el servicio la guarda solo cuando el comercio la publica explícitamente en `metadata.brand`. Categorías, medios y algunos campos auxiliares son opcionales; cuando faltan, se conserva el último valor válido.
- Una búsqueda completa sin resultados no borra filas: la ausencia se registra como indicio en el panel. Las altas quedan `pending_review`.
- El código actual de NEXOR es estático y no tiene una base de productos de tienda que el servicio pueda actualizar. La SQLite del módulo es el almacén nuevo y aislado de datos del proveedor; las coincidencias con el catálogo estático se muestran solo como referencia. Las altas no se publican en la tienda.

### Evidencia pública inicial

En la colección pública `/collections/littmann` se observó “Kit de repuesto Gris para fonendoscopio Littmann” con precio actual de **$109.900 COP**. El catálogo estático de NEXOR contiene ese producto con referencia `40017` y precio `109900` en [catalogo-productos.js](../Assets/Js/catalogo-productos.js). La observación confirma un producto y valor reales, pero representa **paridad**, no un cambio de precio detectado. No se hizo una llamada autenticada UCP ni se creó un run de producción: el perfil/clave privada autorizados no están configurados en este checkout. La primera sincronización real y su historial aparecerán al desplegar el servicio con esa identidad.

## Configuración

Use Python 3.11+ y `pip install -r requirements.txt`. Defina estos valores en el gestor de secretos del servidor (no en el repositorio):

| Variable | Obligatoria | Descripción |
|---|---:|---|
| `NEXOR_UCP_PROFILE_URL` | Sí | URL HTTPS pública del perfil UCP de NEXOR que publica la clave pública registrada. |
| `NEXOR_UCP_PRIVATE_KEY_PATH` | Sí | Ruta protegida a la clave privada ECDSA P-256 correspondiente; nunca la copie al repositorio. |
| `NEXOR_UCP_PRIVATE_KEY_PASSWORD` | No | Contraseña de una clave PEM cifrada. |
| `NEXOR_UCP_SIGNATURE_AGENT_URL` | No | Por defecto usa el perfil UCP y `type=jwks_uri`. |
| `NEXOR_SYNC_ADMIN_TOKEN` | Sí | Token aleatorio de al menos 32 caracteres para el panel/API. |
| `NEXOR_SYNC_DATABASE` | No | SQLite persistente; por defecto `Datos/siempresalud_sync.sqlite3`. |
| `NEXOR_SYNC_HOST` | No | Por defecto `127.0.0.1`; exponga solo detrás de proxy TLS y control de acceso. |
| `NEXOR_SYNC_PORT` | No | Por defecto `8765`. |

El `kid` publicado en el perfil UCP debe corresponder al thumbprint RFC 7638 calculado por el cliente. La clave y perfil deben estar registrados/autorizados para tráfico Web Bot Auth. El servicio falla explícitamente al iniciar si falta una variable obligatoria, la clave no es P-256 o no se puede firmar.

La URL MCP observada en el perfil público es `https://siemsalud.myshopify.com/api/ucp/mcp`. Vuelva a verificar el descubrimiento UCP de la tienda antes de desplegar si el proveedor cambia su endpoint.

## Ejecución local

```powershell
python -m pip install -r requirements.txt
$env:NEXOR_UCP_PROFILE_URL = "https://<dominio-publico-de-nexor>/.well-known/ucp"
$env:NEXOR_UCP_PRIVATE_KEY_PATH = "C:\ruta-segura\nexor-ucp-key.pem"
$env:NEXOR_SYNC_ADMIN_TOKEN = "<token-aleatorio-de-32-o-mas-caracteres>"
python -m Siempresalud_sync
```

Abra `http://127.0.0.1:8765/` e ingrese el token. El scheduler corre dentro del proceso incluso cuando no hay clientes HTTP conectados. Los intervalos son 6 h (disponibilidad), 12 h (precio de referencia) y 24 h (altas, referencias, descripción e imágenes). Una lectura manual ejecuta los tres ámbitos. Se permiten hasta tres intentos por ventana, se respeta `Retry-After` y solo se reintentan fallos temporales. Si la fuente falla, se conservan los últimos valores guardados.

## Despliegue persistente

Use un servidor siempre encendido con almacenamiento persistente para la clave y el archivo SQLite. Mantenga el servicio detrás de HTTPS/reverse proxy, limite el acceso administrativo y aplique respaldo al archivo SQLite (incluidos sus archivos WAL al detener o respaldar con la API de SQLite).

### Linux con systemd

Configure variables en un archivo de entorno con permisos `0600` y una unidad como:

```ini
[Unit]
Description=NEXOR Siempre Salud supplier sync
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/nexor-health
EnvironmentFile=/etc/nexor/siempresalud-sync.env
ExecStart=/opt/nexor-venv/bin/python -m Siempresalud_sync
Restart=always
RestartSec=10
User=nexor-sync
Group=nexor-sync

[Install]
WantedBy=multi-user.target
```

Luego `systemctl enable --now nexor-siempresalud-sync`. Compruebe `systemctl status` y `journalctl -u nexor-siempresalud-sync`.

### Windows Server

Configure las variables como secretos del servicio y cree en Task Scheduler una tarea al iniciar el equipo que ejecute `python.exe -m Siempresalud_sync`, con “Restart on failure”, historial habilitado y una cuenta de servicio de privilegios mínimos. Mantenga el proceso activo (no programe una tarea que termine al finalizar una sesión de usuario). Verifique el estado de la tarea, los registros del servicio y `Datos\siempresalud_sync.sqlite3` tras reiniciar.

No se puede certificar un reinicio de producción desde este repositorio: debe probarse en el host elegido después de configurar el perfil y la clave autorizados.

## API del panel

- `GET /api/dashboard` — métricas, historial, errores y datos del proveedor.
- `POST /api/sync` — inicia sincronización manual; responde 409 si ya hay una ejecución activa.
- Las rutas API exigen `Authorization: Bearer <NEXOR_SYNC_ADMIN_TOKEN>`. No habilite CORS ni publique el puerto sin TLS y control de acceso.

## Validación

`python -m unittest discover -s Siempresalud_sync\Tests` ejecuta pruebas locales del comparador y las reglas de aislamiento. No realiza llamadas al proveedor. Una prueba end-to-end requiere las credenciales autorizadas y un servidor público de perfil UCP; no se debe reportar una sincronización real hasta completar ese paso y conservar la respuesta/run ID en SQLite.
