$utf8 = [System.Text.UTF8Encoding]::new($false)
$text = [System.IO.File]::ReadAllText("GOVERNANCE\A2A_COMMONWEALTH_CHARTER.md", $utf8)
$chinese = [regex]::Matches($text, '[\u4e00-\u9fff]').Count
$english = [regex]::Matches($text, '[a-zA-Z]+').Count
$numbers = [regex]::Matches($text, '\d+').Count
$total = $chinese + $english + $numbers
$lines = ($text -split "`n").Count
Write-Output "中文字符: $chinese"
Write-Output "英文单词: $english"
Write-Output "数字串: $numbers"
Write-Output "总字数: $total"
Write-Output "总行数: $lines"