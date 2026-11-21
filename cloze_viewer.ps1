# Ouvre un XML Moodle (cloze) dans le simulateur cloze local.
# Appele par le clic droit "Ouvrir dans le simulateur cloze" (voir cloze_viewer.reg).
param([Parameter(Mandatory=$true)][string]$Xml)

$viewer = "C:\CloudFred2\GitHub_repository\animations-moodle\cloze-simulateur.html"

$html = [IO.File]::ReadAllText($viewer, [Text.Encoding]::UTF8)
$b64  = [Convert]::ToBase64String([IO.File]::ReadAllBytes($Xml))
$inject = "<script>processContent(new TextDecoder('utf-8').decode(Uint8Array.from(atob('" + $b64 + "'), c => c.charCodeAt(0))));</script>`r`n</body>"

$i   = $html.LastIndexOf('</body>')
$out = $html.Substring(0, $i) + $inject + $html.Substring($i + 7)

$tmp = Join-Path $env:TEMP 'cloze_view.html'
[IO.File]::WriteAllText($tmp, $out, (New-Object Text.UTF8Encoding $false))
Start-Process $tmp
