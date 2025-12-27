# credentials.jsonをBase64エンコードするスクリプト

$credentialsPath = "credentials.json"

if (Test-Path $credentialsPath) {
    $bytes = [System.IO.File]::ReadAllBytes($credentialsPath)
    $base64 = [System.Convert]::ToBase64String($bytes)
    Write-Host "=== Base64エンコード結果 ===" -ForegroundColor Green
    Write-Host $base64
    Write-Host ""
    Write-Host "この値をRenderの環境変数 GOOGLE_CREDENTIALS_BASE64 に設定してください" -ForegroundColor Yellow
} else {
    Write-Host "credentials.json が見つかりません" -ForegroundColor Red
}
