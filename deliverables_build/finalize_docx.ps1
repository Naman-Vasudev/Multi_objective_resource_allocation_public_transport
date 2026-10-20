param([string]$Path, [string]$OutDir)
# Update all fields (TOC, lists of figures/tables, SEQ captions) in Word, export a PDF, and copy the result back.
# Word is pointed at a local copy because saving inside the OneDrive folder hangs the automation.
$Path = (Resolve-Path $Path).Path
New-Item -ItemType Directory -Force $OutDir | Out-Null
$OutDir = (Resolve-Path $OutDir).Path
$work = Join-Path $OutDir ([IO.Path]::GetFileName($Path))
Copy-Item $Path $work -Force
$app = New-Object -ComObject Word.Application
$app.Visible = $false
$app.DisplayAlerts = 0
$app.Options.UpdateLinksAtOpen = $false
try {
    $doc = $app.Documents.Open($work, $false, $false, $false)
    $doc.Fields.Update() | Out-Null
    foreach ($t in $doc.TablesOfContents) { $t.Update() | Out-Null }
    foreach ($t in $doc.TablesOfFigures) { $t.Update() | Out-Null }
    $doc.Fields.Update() | Out-Null
    $doc.Save()
    $pdf = [IO.Path]::ChangeExtension($work, ".pdf")
    $doc.ExportAsFixedFormat($pdf, 17)
    "pages: $($doc.ComputeStatistics(2))"
    $doc.Close($false)
} finally { $app.Quit() }
Copy-Item $work $Path -Force
$pdf
