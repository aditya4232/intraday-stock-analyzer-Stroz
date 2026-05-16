$env:STREAMLIT_SERVER_HEADLESS = "true"
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
$env:STREAMLIT_SERVER_PORT = "8500"
$env:STREAMLIT_THEME_BASE = "dark"

$pythonExe = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonExe) {
    Write-Error "Python not found in PATH. Please install Python 3.10+ and add it to PATH."
    exit 1
}

$p = Start-Process -NoNewWindow -FilePath $pythonExe.Source -ArgumentList "-m streamlit run intraday-scanner/app.py" -RedirectStandardOutput "app_out.txt" -RedirectStandardError "app_err.txt" -PassThru
Write-Output "PID: $($p.Id)"
Write-Output "App running at http://localhost:8500"
