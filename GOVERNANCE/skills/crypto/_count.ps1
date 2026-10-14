$files = @('pqc-assessment.md','crypto-law-compliance.md','gm-algorithm.md','rhel10-crypto.md','key-lifecycle.md')
$base = $PSScriptRoot + '\'
$marker = '### ' + [char]0x81EA + [char]0x6211 + [char]0x8BC4 + [char]0x4F30
foreach ($f in $files) {
  $t = Get-Content -Raw -Encoding UTF8 ($base + $f)
  $body = ($t -split [regex]::Escape($marker))[0]
  $n = ([regex]::Matches($body, '[\u4e00-\u9fff]')).Count
  Write-Output ($f + ' body-hanzi=' + $n)
}
