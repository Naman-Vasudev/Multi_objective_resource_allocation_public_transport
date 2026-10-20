param([string]$Path, [string]$OutDir, [int]$Width = 1280)
# Render a .pptx to PNG per slide, or a .docx to PDF, using Microsoft Office COM.
$Path = (Resolve-Path $Path).Path
New-Item -ItemType Directory -Force $OutDir | Out-Null
$OutDir = (Resolve-Path $OutDir).Path
if ($Path -like "*.pptx") {
    $app = New-Object -ComObject PowerPoint.Application
    $pres = $app.Presentations.Open($Path, $true, $false, $false)   # read-only, no window
    $h = [int]($Width * $pres.PageSetup.SlideHeight / $pres.PageSetup.SlideWidth)
    foreach ($s in $pres.Slides) {
        $s.Export((Join-Path $OutDir ("slide-{0:D2}.png" -f $s.SlideIndex)), "PNG", $Width, $h)
    }
    "slides: $($pres.Slides.Count)"
    $pres.Close(); $app.Quit()
} elseif ($Path -like "*.docx") {
    $app = New-Object -ComObject Word.Application
    $app.Visible = $false
    $doc = $app.Documents.Open($Path, $false, $true)
    $pdf = Join-Path $OutDir (([IO.Path]::GetFileNameWithoutExtension($Path)) + ".pdf")
    $doc.ExportAsFixedFormat($pdf, 17)
    "pages: $($doc.ComputeStatistics(2))"
    $doc.Close($false); $app.Quit()
    $pdf
}
