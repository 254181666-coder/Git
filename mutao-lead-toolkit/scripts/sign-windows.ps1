param(
  [Parameter(Mandatory=$true)][string]$File,
  [Parameter(Mandatory=$true)][string]$CertPath,
  [Parameter(Mandatory=$true)][string]$CertPassword,
  [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$signtool = "signtool.exe"

& $signtool sign `
  /f $CertPath `
  /p $CertPassword `
  /fd SHA256 `
  /tr $TimestampUrl `
  /td SHA256 `
  $File

if ($LASTEXITCODE -ne 0) {
  throw "签名失败：$File"
}

& $signtool verify /pa /v $File
