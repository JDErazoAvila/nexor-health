<#
  NEXOR · Instalador y ejecutor del scraper de Temu (PowerShell 5.1+ / Windows)
  =============================================================================
  Uso:
    powershell -ExecutionPolicy Bypass -File instalar-temu.ps1 -SoloInstalar
        -> instala Python (si falta), pip, playwright y Chromium
    powershell -ExecutionPolicy Bypass -File instalar-temu.ps1
        -> instala lo necesario y luego corre el scraper
    powershell -ExecutionPolicy Bypass -File instalar-temu.ps1 -Consulta "guantes nitrilo 100"
        -> igual pero con una búsqueda libre
#>
param(
  [switch]$SoloInstalar,
  [string]$Consulta = ""
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$requirementsPath = Join-Path $repoRoot 'requirements.txt'
$scraperPath = Join-Path $PSScriptRoot 'scraper_temu.py'
$calculatorPath = Join-Path $repoRoot 'Herramientas\Precios\calcular-precios.html'
if (-not (Test-Path $requirementsPath)) {
  throw "No se encontró el archivo de dependencias: $requirementsPath"
}
if (-not (Test-Path $scraperPath)) {
  throw "No se encontró el scraper requerido: $scraperPath"
}

function Comprobar-Python {
  foreach ($cmd in @("python", "py", "python3")) {
    try {
      $v = & $cmd --version 2>&1
      if ($LASTEXITCODE -eq 0 -and "$v" -match "Python") {
        return $cmd
      }
    } catch { }
  }
  return $null
}

Write-Host ""
Write-Host "=== NEXOR: instalador y ejecutor del scraper de Temu ===" -ForegroundColor Cyan

$pythonCmd = Comprobar-Python
if (-not $pythonCmd) {
  Write-Host ""
  Write-Host "No tienes Python instalado. Hay dos formas de instalarlo:" -ForegroundColor Yellow
  Write-Host "  A) (recomendada) En PowerShell ejecuta:" -ForegroundColor White
  Write-Host "       winget install --id Python.Python.3.12 -e --source winget" -ForegroundColor Green
  Write-Host "  B) Ve a https://www.python.org/downloads/ , descarga Python 3.12 y" -ForegroundColor White
  Write-Host "     marca la casilla 'Add Python to PATH' antes de instalar." -ForegroundColor White
  Write-Host ""
  Write-Host "Después cierra y abre PowerShell, entra a la raíz del proyecto y ejecuta:" -ForegroundColor Cyan
  Write-Host "    powershell -ExecutionPolicy Bypass -File .\Herramientas\Scraping-Temu\instalar.ps1 -SoloInstalar" -ForegroundColor White
  exit 1
}

Write-Host ("Python detectado: " + $pythonCmd) -ForegroundColor Green

Write-Host "`n[1/4] Actualizando pip..."
& $pythonCmd -m pip install --upgrade pip --quiet

Write-Host "[2/4] Instalando playwright..."
& $pythonCmd -m pip install -r $requirementsPath --quiet

Write-Host "[3/4] Descargando el navegador Chromium (puede tardar 1-2 minutos)..."
& $pythonCmd -m playwright install chromium

Write-Host "[4/4] Probando que el scraper compila..."
& $pythonCmd -m py_compile $scraperPath
Write-Host "      Compilación OK" -ForegroundColor Green

if ($SoloInstalar) {
  Write-Host ""
  Write-Host "Todo listo. Para buscar los 10 productos ejecuta:" -ForegroundColor Green
  Write-Host "    powershell -ExecutionPolicy Bypass -File .\Herramientas\Scraping-Temu\instalar.ps1" -ForegroundColor White
  exit 0
}

$extraArgs = @()
if ($Consulta -ne "") {
  $extraArgs += "--query"
  $extraArgs += $Consulta
}

Write-Host ""
Write-Host "Iniciando el scraper..." -ForegroundColor Green
Write-Host "Si aparece la verificación de seguridad de Temu, resuélvela a mano y continúa solo.`n" -ForegroundColor Yellow

& $pythonCmd $scraperPath @extraArgs

if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "El scraper terminó con error. Revisa el mensaje de arriba." -ForegroundColor Yellow
  Write-Host "Alternativa rápida: abre Temu en modo incógnito, copia los precios y úsalo" -ForegroundColor White
  Write-Host "en la calculadora '$calculatorPath'." -ForegroundColor White
}