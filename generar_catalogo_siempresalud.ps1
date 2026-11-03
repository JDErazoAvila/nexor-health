$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem

$workbookPath = Join-Path $PSScriptRoot 'siempresalud_catalogo_completo.xlsx'
$outputPath = Join-Path $PSScriptRoot 'productos_siempresalud_catalogo.js'
if (-not (Test-Path $workbookPath)) {
  throw "No se encontró el archivo fuente: $workbookPath"
}

$archive = [System.IO.Compression.ZipFile]::OpenRead($workbookPath)
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

  $productRows = Read-Worksheet 'xl/worksheets/sheet1.xml'
  $variantRows = Read-Worksheet 'xl/worksheets/sheet2.xml'
  if ($productRows.Count -lt 2 -or $variantRows.Count -lt 2) {
    throw "Las hojas Productos o Variantes no contienen datos (Productos: $($productRows.Count), Variantes: $($variantRows.Count))."
  }

  $variantsByProduct = @{}
  foreach ($row in ($variantRows | Select-Object -Skip 1)) {
    $productUrl = [string]$row['K']
    if (-not $variantsByProduct.ContainsKey($productUrl)) {
      $variantsByProduct[$productUrl] = [System.Collections.Generic.List[object]]::new()
    }
    $variantName = [string]$row['E']
    $variantsByProduct[$productUrl].Add([ordered]@{
      name = $variantName
      sku = [string]$row['C']
      price = Convert-Price $row['F']
      available = ([string]$row['H'] -eq '1')
    })
  }

  $catalog = [System.Collections.Generic.List[object]]::new()
  foreach ($row in ($productRows | Select-Object -Skip 1)) {
    $productId = [string]$row['A']
    $productUrl = [string]$row['O']
    $categoryPath = @(([string]$row['Q'] -split '\s*\|\s*') | Where-Object { $_ })
    $productType = [string]$row['D']
    $category = if ($categoryPath.Count) { $categoryPath[0] } else { $productType }
    $brand = if ($categoryPath.Count -gt 1) { $categoryPath[-1] } else { '' }
    $images = @(
      ([string]$row['H'] -split '\s*\|\s*') |
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
      $currentPrice = Convert-Price $row['E']
      $priceLabel = ''
    }
    $catalog.Add([ordered]@{
      id = if ($row['P']) { [string]$row['P'] } else { $productId }
      name = [string]$row['B']
      reference = $reference
      category = $category
      categories = $categoryPath
      brand = $brand
      productType = $productType
      description = [string]$row['G']
      price = $currentPrice
      priceLabel = $priceLabel
      priceUnitLabel = 'producto'
      quantityUnit = 'unidades'
      specifications = $productType
      image = if ($images.Count) { $images[0] } else { '' }
      images = $images
      available = ([string]$row['L'] -eq '1')
      rating = Convert-Price $row['M']
      reviewCount = Convert-Price $row['N']
      variants = $variants
    })
  }

  $json = ConvertTo-Json -InputObject $catalog.ToArray() -Depth 8 -Compress
  $javascript = "window.NEXOR_PRODUCTS = $json;`n"
  [System.IO.File]::WriteAllText($outputPath, $javascript, [System.Text.UTF8Encoding]::new($false))
  Write-Output "Catálogo generado: $($catalog.Count) productos, $($variantRows.Count - 1) variantes."
} finally {
  $archive.Dispose()
}
