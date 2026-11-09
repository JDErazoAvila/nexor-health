$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$rates = Import-Csv -Encoding UTF8 -Delimiter ';' (Join-Path $root 'Datos\tarifas-envio-referencia.csv')
$packages = Import-Csv -Encoding UTF8 -Delimiter ';' (Join-Path $root 'Datos\estimaciones-paquetes.csv')
$destinationCodes = @{
    'Cali' = '76001'; 'Palmira' = '76520'; 'Yumbo' = '76892'; 'Jamundí' = '76364'
    'Tuluá' = '76834'; 'Cartago' = '76147'; 'Buenaventura' = '76109'; 'Alcalá' = '76020'
    'Andalucía' = '76036'; 'Ansermanuevo' = '76041'; 'Argelia (Valle del Cauca)' = '76054'
    'Bolívar (Valle del Cauca)' = '76100'; 'Buga' = '76111'; 'Bugalagrande' = '76113'
    'Caicedonia' = '76122'; 'Calima Darién' = '76126'; 'Dagua' = '76233'
    'El Águila' = '76243'; 'Medellín' = '05001'; 'Bogotá' = '11001'; 'Barranquilla' = '08001'
}
$byCity = @{}
foreach ($row in $rates) {
    if ($row.origen -ne 'Cali' -or $row.referencia_paquete -ne 'Par de zapatos: 50 x 38 x 42 cm' -or -not $row.tarifa_cop) { continue }
    if ($row.fecha -ne '2026-11-09' -or $row.peso_kg -ne '1' -or $row.valor_declarado_cop -ne '100000' -or $row.servicio -ne 'Mensajería estándar' -or $row.entrega -ne 'Dirección' -or $row.paga -ne 'Remitente') { throw "Los supuestos de la tarifa cambiaron: $($row.destino)" }
    if (-not $destinationCodes.ContainsKey($row.destino)) { throw "Destino sin código DIVIPOLA: $($row.destino)" }
    $code = $destinationCodes[$row.destino]
    if ($byCity.ContainsKey($code)) { throw "Tarifa duplicada para $code" }
    $amount = 0
    if (-not [int]::TryParse($row.tarifa_cop, [ref]$amount) -or $amount -le 0) { throw "Tarifa inválida para $code" }
    $byCity[$code] = $amount
}
if ($byCity.Count -ne $destinationCodes.Count) { throw 'Faltan tarifas de referencia esperadas.' }
$eligible = @()
$ids = @{}
foreach ($row in $packages) {
    if (-not $row.id_producto -or $ids.ContainsKey($row.id_producto)) { throw "Identificador ausente o duplicado: $($row.id_producto)" }
    $ids[$row.id_producto] = $true
    if ($row.estado -ne 'supuesto no verificado') { continue }
    $weight = 0.0
    if (-not [double]::TryParse($row.peso_min_kg, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$weight)) { throw "Peso inválido: $($row.id_producto)" }
    $dimensions = @($row.caja_ejemplo_cm -split '\s*x\s*' | ForEach-Object { [double]::Parse($_, [Globalization.CultureInfo]::InvariantCulture) } | Sort-Object -Descending)
    if ($dimensions.Count -ne 3) { throw "Dimensiones inválidas: $($row.id_producto)" }
    if ($weight -le 1 -and $dimensions[0] -le 50 -and $dimensions[1] -le 42 -and $dimensions[2] -le 38) { $eligible += $row.id_producto }
}
if (-not $eligible.Count) { throw 'No hay productos con supuesto compatible.' }
$data = @{ origin = 'Cali'; date = '2026-11-09'; rates = $byCity; eligibleProductIds = @($eligible) } | ConvertTo-Json -Depth 5 -Compress
$output = Join-Path $root 'Assets\Js\referencias-envio.js'
[IO.File]::WriteAllText($output, "window.NEXOR_SHIPPING_REFERENCES = $data;`n", [Text.UTF8Encoding]::new($false))
Write-Output "Rutas: $($byCity.Count). Productos con supuesto compatible: $($eligible.Count)."
