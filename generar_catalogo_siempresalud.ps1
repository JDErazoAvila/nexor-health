$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$saleDiscount = 0.30
$workbookPath = Join-Path $PSScriptRoot 'siempresalud_catalogo_completo.xlsx'
$outputPath = Join-Path $PSScriptRoot 'productos_siempresalud_catalogo.js'
if (-not (Test-Path $workbookPath)) {
  throw "No se encontró el archivo fuente: $workbookPath"
}

$workbookStream = [System.IO.File]::Open($workbookPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
$archive = [System.IO.Compression.ZipArchive]::new($workbookStream, [System.IO.Compression.ZipArchiveMode]::Read)
try {
  function Read-WorkbookEntry([string]$Name) {
    $entry = $archive.GetEntry($Name)
    if (-not $entry) { return $null }
    $reader = [System.IO.StreamReader]::new($entry.Open())
    try { return $reader.ReadToEnd() }
    finally { $reader.Dispose() }
  }

  $sharedStrings = [System.Collections.Generic.List[string]]::new()
  $sharedXml = Read-WorkbookEntry 'xl/sharedStrings.xml'
  if ($sharedXml) {
    $sharedDocument = [xml]$sharedXml
    $sharedNamespaces = [System.Xml.XmlNamespaceManager]::new($sharedDocument.NameTable)
    $sharedNamespaces.AddNamespace('m', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')
    foreach ($item in $sharedDocument.SelectNodes('//m:si', $sharedNamespaces)) {
      $sharedStrings.Add((($item.SelectNodes('.//m:t', $sharedNamespaces) | ForEach-Object { $_.InnerText }) -join ''))
    }
  }

  function Read-Worksheet([string]$EntryName) {
    $sheetXml = Read-WorkbookEntry $EntryName
    if (-not $sheetXml) { throw "No se encontró la sección $EntryName en el archivo Excel." }
    $document = [xml]$sheetXml
    $namespaces = [System.Xml.XmlNamespaceManager]::new($document.NameTable)
    $namespaces.AddNamespace('m', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')
    $rows = [System.Collections.Generic.List[hashtable]]::new()
    foreach ($row in $document.SelectNodes('//m:sheetData/m:row', $namespaces)) {
      $values = @{}
      foreach ($cell in $row.SelectNodes('m:c', $namespaces)) {
        $column = [regex]::Match($cell.r, '^[A-Z]+').Value
        $value = $cell.SelectSingleNode('m:v', $namespaces)
        if ($cell.t -eq 's' -and $value) {
          $values[$column] = $sharedStrings[[int]$value.InnerText]
        } elseif ($cell.t -eq 'inlineStr') {
          $values[$column] = ($cell.SelectNodes('.//m:t', $namespaces) | ForEach-Object { $_.InnerText }) -join ''
        } elseif ($value) {
          $values[$column] = $value.InnerText
        }
      }
      $rows.Add($values)
    }
    return ,$rows.ToArray()
  }

  function Convert-Price($Value) {
    if ([string]::IsNullOrWhiteSpace([string]$Value)) { return $null }
    $number = 0.0
    $parsed = [double]::TryParse(
      [string]$Value,
      [System.Globalization.NumberStyles]::Float,
      [System.Globalization.CultureInfo]::InvariantCulture,
      [ref]$number
    )
    if ($parsed) { return $number }
    return $null
  }

  function Convert-SalePrice($Value, [bool]$ApplyDiscount = $true) {
    $number = Convert-Price $Value
    if ($null -eq $number) { return $null }
    if (-not $ApplyDiscount) { return $number }
    return [math]::Round($number * (1 - $saleDiscount), 0, [System.MidpointRounding]::AwayFromZero)
  }

  function Find-Column([hashtable]$HeaderRow, [string[]]$Names, [string]$FieldName) {
    foreach ($name in $Names) {
      foreach ($column in $HeaderRow.Keys) {
        $headerKey = ([string]$HeaderRow[$column] -replace '[^A-Za-z0-9]', '')
        $nameKey = ($name -replace '[^A-Za-z0-9]', '')
        if ($headerKey -ieq $nameKey) { return $column }
      }
    }
    throw "No se encontró la columna '$FieldName' en el archivo Excel."
  }

  $productRows = Read-Worksheet 'xl/worksheets/sheet1.xml'
  $variantRows = Read-Worksheet 'xl/worksheets/sheet2.xml'
  if ($productRows.Count -lt 2 -or $variantRows.Count -lt 2) {
    throw "Las hojas Productos o Variantes no contienen datos (Productos: $($productRows.Count), Variantes: $($variantRows.Count))."
  }

  $productHeaders = $productRows[0]
  $productColumns = @{
    id = Find-Column $productHeaders @('Handle') 'Handle'
    fallbackId = Find-Column $productHeaders @('ID Shopify') 'ID Shopify'
    name = Find-Column $productHeaders @('Nombre') 'Nombre'
    type = Find-Column $productHeaders @('Tipo de producto') 'Tipo de producto'
    basePrice = Find-Column $productHeaders @('Precio actual mínimo', 'precio_NEXOR') 'Precio actual mínimo'
    description = Find-Column $productHeaders @('Descripción') 'Descripción'
    images = Find-Column $productHeaders @('Imágenes') 'Imágenes'
    url = Find-Column $productHeaders @('URL') 'URL'
    categories = Find-Column $productHeaders @('Categorías') 'Categorías'
    available = Find-Column $productHeaders @('Disponibilidad general') 'Disponibilidad general'
    rating = Find-Column $productHeaders @('Calificación') 'Calificación'
    reviewCount = Find-Column $productHeaders @('Número de reseñas') 'Número de reseñas'
  }
  $variantHeaders = $variantRows[0]
  $variantColumns = @{
    sku = Find-Column $variantHeaders @('SKU') 'SKU'
    name = Find-Column $variantHeaders @('Variante') 'Variante'
    price = Find-Column $variantHeaders @('Precio') 'Precio'
    available = Find-Column $variantHeaders @('Disponibilidad') 'Disponibilidad'
    url = Find-Column $variantHeaders @('URL') 'URL'
  }

  $brandByProductUrl = @{}
  foreach ($row in ($productRows | Select-Object -Skip 1)) {
    $categoryPath = @(([string]$row[$productColumns.categories] -split '\s*\|\s*') | Where-Object { $_ })
    $brandByProductUrl[[string]$row[$productColumns.url]] = if ($categoryPath.Count -gt 1) { $categoryPath[-1] } else { '' }
  }

  $variantsByProduct = @{}
  foreach ($row in ($variantRows | Select-Object -Skip 1)) {
    $productUrl = [string]$row[$variantColumns.url]
    if (-not $variantsByProduct.ContainsKey($productUrl)) {
      $variantsByProduct[$productUrl] = [System.Collections.Generic.List[object]]::new()
    }
    $variantName = [string]$row[$variantColumns.name]
    $isLittmann = $brandByProductUrl[$productUrl] -ieq 'Littmann'
    $variantsByProduct[$productUrl].Add([ordered]@{
      name = $variantName
      sku = [string]$row[$variantColumns.sku]
      price = Convert-SalePrice $row[$variantColumns.price] (-not $isLittmann)
      available = ([string]$row[$variantColumns.available] -eq '1')
    })
  }

  $catalog = [System.Collections.Generic.List[object]]::new()
  foreach ($row in ($productRows | Select-Object -Skip 1)) {
    $productId = [string]$row[$productColumns.fallbackId]
    $productUrl = [string]$row[$productColumns.url]
    $categoryPath = @(([string]$row[$productColumns.categories] -split '\s*\|\s*') | Where-Object { $_ })
    $productType = [string]$row[$productColumns.type]
    $category = if ($categoryPath.Count) { $categoryPath[0] } else { $productType }
    $brand = if ($categoryPath.Count -gt 1) { $categoryPath[-1] } else { '' }
    $images = @(
      ([string]$row[$productColumns.images] -split '\s*\|\s*') |
        ForEach-Object {
          $imageUrl = $_.Trim()
          if ($imageUrl.StartsWith('//')) { $imageUrl = 'https:' + $imageUrl }
          if ($imageUrl -match '^https?://') { $imageUrl }
        } |
        Select-Object -Unique
    )
    $variants = @()
    if ($variantsByProduct.ContainsKey($productUrl)) {
      $variants = $variantsByProduct[$productUrl].ToArray()
    }
    $reference = ''
    foreach ($variant in $variants) {
      if ($variant.sku) { $reference = $variant.sku; break }
    }
    $availablePrices = @($variants | Where-Object { $_.available -and $null -ne $_.price } | ForEach-Object { $_.price } | Select-Object -Unique)
    if ($availablePrices.Count) {
      $currentPrice = ($availablePrices | Measure-Object -Minimum).Minimum
      $priceLabel = if ($availablePrices.Count -gt 1) { 'Desde' } else { '' }
    } else {
      $currentPrice = Convert-SalePrice $row[$productColumns.basePrice] ($brand -ine 'Littmann')
      $priceLabel = ''
    }
    $catalog.Add([ordered]@{
      id = if ($row[$productColumns.id]) { [string]$row[$productColumns.id] } else { $productId }
      name = [string]$row[$productColumns.name]
      reference = $reference
      category = $category
      categories = $categoryPath
      brand = $brand
      productType = $productType
      description = [string]$row[$productColumns.description]
      price = $currentPrice
      priceLabel = $priceLabel
      priceUnitLabel = 'producto'
      quantityUnit = 'unidades'
      specifications = $productType
      image = if ($images.Count) { $images[0] } else { '' }
      images = $images
      available = ([string]$row[$productColumns.available] -eq '1')
      rating = Convert-Price $row[$productColumns.rating]
      reviewCount = Convert-Price $row[$productColumns.reviewCount]
      variants = $variants
    })
  }

  $json = ConvertTo-Json -InputObject $catalog.ToArray() -Depth 8 -Compress
  $javascript = "window.NEXOR_PRODUCTS = $json;`n"
  [System.IO.File]::WriteAllText($outputPath, $javascript, [System.Text.UTF8Encoding]::new($false))
  Write-Output "Catálogo generado: $($catalog.Count) productos, $($variantRows.Count - 1) variantes; 30 % de descuento aplicado excepto a Littmann."
} finally {
  $archive.Dispose()
}
