[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   ENTERPRISE AUTOMATION - SYSTEM ENVIRONMENT CHECK" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Java Check
Write-Host "[1] Kiểm tra Java Runtime Environment..." -NoNewline
try {
    $javaVer = java -version 2>&1 | Out-String
    Write-Host " [OK]" -ForegroundColor Green
    Write-Host "    $($javaVer.Split("`n")[0].Trim())" -ForegroundColor Gray
} catch {
    Write-Host " [FAIL]" -ForegroundColor Red
}

# 2. Chrome Check
Write-Host "[2] Kiểm tra Google Chrome..." -NoNewline
$chromePath = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "${env:LocalAppData}\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($chromePath) {
    $ver = (Get-Item $chromePath).VersionInfo.FileVersion
    Write-Host " [OK]" -ForegroundColor Green
    Write-Host "    Version: $ver ($chromePath)" -ForegroundColor Gray
} else {
    Write-Host " [NOT FOUND]" -ForegroundColor Yellow
}

# 3. Katalon Studio / KRE Check
Write-Host "[3] Kiểm tra Katalon Studio / KRE..." -NoNewline
$katalonCmd = Get-Command katalonc -ErrorAction SilentlyContinue
if (-not $katalonCmd) { $katalonCmd = Get-Command katalon -ErrorAction SilentlyContinue }
$katalonExec = if ($katalonCmd) { $katalonCmd.Source } else { $null }

if (-not $katalonExec) {
    $possiblePaths = @(
        $env:KATALON_HOME,
        "C:\Katalon_Studio_Engine",
        "C:\Katalon_Studio",
        "D:\Katalon_Studio_Engine",
        "D:\Katalon_Studio"
    )
    foreach ($p in $possiblePaths) {
        if ($p -and (Test-Path "$p\katalonc.exe")) {
            $katalonExec = "$p\katalonc.exe"
            break
        }
    }
}

if ($katalonExec) {
    Write-Host " [OK]" -ForegroundColor Green
    Write-Host "    Path: $katalonExec" -ForegroundColor Gray
} else {
    Write-Host " [KRE không tìm thấy! Vui lòng cài đặt hoặc thiết lập KATALON_HOME]" -ForegroundColor Yellow
}

# 4. Allure Check
Write-Host "[4] Kiểm tra Allure CLI..." -NoNewline
$allureCmd = Get-Command allure -ErrorAction SilentlyContinue
if ($allureCmd) {
    Write-Host " [OK]" -ForegroundColor Green
} else {
    Write-Host " [Chưa cài đặt Allure CLI - Báo cáo HTML sẽ dựa trên Katalon Report]" -ForegroundColor Yellow
}

# 5. Environment Variables Check
Write-Host "[5] Kiểm tra biến môi trường cấu hình:"
$baseUrl = $env:BASE_URL
if (-not $baseUrl) { $baseUrl = "https://app.example.com (Mặc định)" }
Write-Host "    BASE_URL: $baseUrl" -ForegroundColor Cyan

$user = $env:APP_USERNAME
if (-not $user) { $user = $env:APP_USER }
if (-not $user) { $user = "admin_nan (Mặc định trong Profiles/default.glbl)" }
Write-Host "    USERNAME: $user" -ForegroundColor Cyan

$pwd = $env:APP_PASSWORD
if (-not $pwd) { $pwd = $env:PASSWORD_Enterprise }
if ($pwd) {
    Write-Host "    PASSWORD: [ĐÃ THIẾT LẬP]" -ForegroundColor Green
} else {
    Write-Host "    PASSWORD: [CHƯA THIẾT LẬP] (Cần APP_PASSWORD để đăng nhập trên Jenkins)" -ForegroundColor Yellow
}

$apiKey = $env:KATALON_API_KEY
if ($apiKey) {
    Write-Host "    KATALON_API_KEY: [ĐÃ THIẾT LẬP]" -ForegroundColor Green
} else {
    Write-Host "    KATALON_API_KEY: [CHƯA THIẾT LẬP] (Cần nếu chạy KRE có bản quyền)" -ForegroundColor Gray
}

$telegramToken = $env:TELEGRAM_BOT_TOKEN
if ($telegramToken) {
    Write-Host "    TELEGRAM_BOT_TOKEN: [ĐÃ THIẾT LẬP]" -ForegroundColor Green
} else {
    Write-Host "    TELEGRAM_BOT_TOKEN: [CHƯA CẤU HÌNH] (Bỏ qua gửi Telegram)" -ForegroundColor Gray
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Kiểm tra hoàn tất." -ForegroundColor Green
