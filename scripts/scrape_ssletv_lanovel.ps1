param(
  [int]$TargetCount = 40,
  [string]$OutputPath = "data/lanovel_posts.json"
)

$ErrorActionPreference = "Stop"

function Normalize-Text {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }

  $t = $Text -replace "<script[\s\S]*?</script>", ""
  $t = $t -replace "<style[\s\S]*?</style>", ""
  $t = $t -replace "<br\s*/?>", "`n"
  $t = $t -replace "</p>", "`n"
  $t = $t -replace "<[^>]+>", ""
  $t = [System.Net.WebUtility]::HtmlDecode($t)
  $t = $t -replace "\r", ""
  $t = $t -replace "\n{3,}", "`n`n"
  return $t.Trim()
}

function First-Match {
  param(
    [string]$Input,
    [string[]]$Patterns
  )
  foreach ($p in $Patterns) {
    $m = [regex]::Match($Input, $p, [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if ($m.Success) {
      return $m.Groups[1].Value
    }
  }
  return ""
}

function Distinct-List {
  param([string[]]$Items)
  $set = New-Object 'System.Collections.Generic.HashSet[string]'
  $out = New-Object System.Collections.Generic.List[string]
  foreach ($i in $Items) {
    if ([string]::IsNullOrWhiteSpace($i)) { continue }
    if ($set.Add($i)) { $out.Add($i) }
  }
  return $out
}

$base = "https://www.ssletv.com/category/%EB%9D%BC%EB%85%B8%EB%B2%A8/%EB%9D%BC%EB%85%B8%EB%B2%A8%20%EC%A0%95%EB%B3%B4"
$entryUrls = New-Object System.Collections.Generic.List[string]

for ($p = 1; $p -le 25; $p++) {
  $url = if ($p -eq 1) { $base } else { "$base?page=$p" }
  try {
    $res = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 20
    $matches = [regex]::Matches($res.Content, 'https://www\.ssletv\.com/entry/[^"''\s<]+')
    foreach ($m in $matches) {
      if (-not $entryUrls.Contains($m.Value)) {
        $entryUrls.Add($m.Value)
      }
      if ($entryUrls.Count -ge $TargetCount) { break }
    }
    if ($entryUrls.Count -ge $TargetCount) { break }
  } catch {
    Write-Host "[warn] failed page $p"
  }
  Start-Sleep -Milliseconds 250
}

$items = New-Object System.Collections.Generic.List[object]

foreach ($u in $entryUrls) {
  if ($items.Count -ge $TargetCount) { break }
  try {
    $res = Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 20
    $html = $res.Content

    $title = First-Match -Input $html -Patterns @(
      '<meta property="og:title" content="([^"]+)"',
      '<title>([^<]+)</title>',
      '<h1[^>]*>(.*?)</h1>'
    )

    $published = First-Match -Input $html -Patterns @(
      '<meta property="article:published_time" content="([^"]+)"',
      '<span class="txt_info">([^<]+)</span>'
    )

    $contentRaw = First-Match -Input $html -Patterns @(
      '<div class="tt_article_useless_p_margin[^"]*">([\s\S]*?)<div class="container_postbtn',
      '<div class="entry-content">([\s\S]*?)</div>\s*</div>\s*</article>',
      '<article[\s\S]*?<div class="contents_style">([\s\S]*?)</div>'
    )

    $ncodeUrl = First-Match -Input $contentRaw -Patterns @(
      '(https?://ncode\.syosetu\.com/[^"''\s<]+)',
      '(https?://novel18\.syosetu\.com/[^"''\s<]+)'
    )

    $imgMatches = [regex]::Matches($contentRaw, '<img[^>]+src="([^"]+)"', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    $rawImgs = New-Object System.Collections.Generic.List[string]
    foreach ($m in $imgMatches) {
      if ($m.Groups[1].Success) { $rawImgs.Add($m.Groups[1].Value) }
    }
    $imageUrls = Distinct-List -Items $rawImgs

    $content = Normalize-Text -Text $contentRaw
    if ([string]::IsNullOrWhiteSpace($content)) { continue }

    $idSeed = [System.Text.Encoding]::UTF8.GetBytes($u)
    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    $hash = ($sha1.ComputeHash($idSeed) | ForEach-Object { $_.ToString('x2') }) -join ''

    $items.Add([ordered]@{
      id = "lnv-" + $hash.Substring(0, 12)
      title = $title.Trim()
      source_url = $u
      source_site = "ssletv"
      published_at = ($published -replace "\.", "-").Trim()
      category = "라노벨 정보"
      excerpt = if ($content.Length -gt 260) { $content.Substring(0, 260) } else { $content }
      content = if ($content.Length -gt 12000) { $content.Substring(0, 12000) } else { $content }
      ncode_url = $ncodeUrl
      image_urls = $imageUrls
      fetched_at = (Get-Date).ToString("s")
    })

    Write-Host "[ok] $($items.Count): $title"
  } catch {
    Write-Host "[warn] failed entry: $u"
  }
  Start-Sleep -Milliseconds 300
}

$dir = Split-Path -Path $OutputPath -Parent
if ($dir -and -not (Test-Path $dir)) {
  New-Item -ItemType Directory -Path $dir | Out-Null
}

$items | ConvertTo-Json -Depth 6 | Set-Content -Path $OutputPath -Encoding UTF8
Write-Host "[done] wrote $($items.Count) entries to $OutputPath"
