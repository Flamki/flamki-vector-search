<#
.SYNOPSIS
  Record demo showcase + mux with existing ElevenLabs voiceover.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts/render_final_submission.ps1
#>
param(
    [string]$VoiceMp3   = 'recordings/demo_voiceover.mp3',
    [string]$FinalVideo = 'recordings/final_submission_demo.mp4',
    [int]$ServerPort    = 8787
)
$ErrorActionPreference = 'Stop'

function Get-PrimaryBounds {
    Add-Type -AssemblyName System.Windows.Forms
    return [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
}
Add-Type @"
using System; using System.Runtime.InteropServices;
public static class DWA {
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int X, int Y, int cx, int cy, uint f);
}
"@

if (-not (Test-Path $VoiceMp3)) { throw "Voiceover not found: $VoiceMp3" }
$voiceSec = [double]::Parse((ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $VoiceMp3).Trim(), [System.Globalization.CultureInfo]::InvariantCulture)
$recordSec = [int][Math]::Ceiling($voiceSec + 5)
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$rawVideo = "recordings/raw_submission_$ts.mp4"

Write-Host "`n=== FLAMKI FINAL SUBMISSION RENDER ===" -ForegroundColor Cyan
Write-Host "Voice: $VoiceMp3 ($([Math]::Round($voiceSec,1))s)"
Write-Host "Record: ${recordSec}s | Raw: $rawVideo | Final: $FinalVideo`n"

# Start showcase server
$srv = Start-Process python -ArgumentList '-m','http.server',"$ServerPort",'--bind','127.0.0.1' -WorkingDirectory (Get-Location).Path -PassThru -WindowStyle Hidden
$profDir = Join-Path $env:TEMP ("flamki_$ts")
New-Item -ItemType Directory -Path $profDir | Out-Null

try {
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {
        try { $r = Invoke-WebRequest -Uri "http://127.0.0.1:$ServerPort/scripts/demo_showcase/index.html" -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -lt 500) { break } } catch {}
        Start-Sleep -Milliseconds 500
    }
    Write-Host '[OK] Showcase server ready' -ForegroundColor Green

    # Minimize all, open Edge in app mode
    try { (New-Object -ComObject Shell.Application).MinimizeAll() | Out-Null } catch {}
    Start-Process msedge -ArgumentList "--user-data-dir=$profDir",'--no-first-run','--disable-gpu',"--app=http://127.0.0.1:$ServerPort/scripts/demo_showcase/index.html"

    $deadline = (Get-Date).AddSeconds(20)
    $bounds = Get-PrimaryBounds
    $wShell = New-Object -ComObject WScript.Shell
    while ((Get-Date) -lt $deadline) {
        $p = Get-Process msedge -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like '*Flamki*' } | Select-Object -First 1
        if ($p) {
            [DWA]::ShowWindow($p.MainWindowHandle, 3) | Out-Null
            [DWA]::SetWindowPos($p.MainWindowHandle, [IntPtr](-1), $bounds.X, $bounds.Y, $bounds.Width, $bounds.Height, 0x0040) | Out-Null
            [DWA]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
            $null = $wShell.AppActivate($p.Id)
            break
        }
        Start-Sleep -Milliseconds 500
    }
    Write-Host '[OK] Showcase window maximized' -ForegroundColor Green
    Start-Sleep -Seconds 2

    # Record screen
    Write-Host "[..] Recording ${recordSec}s..." -ForegroundColor Yellow
    $ffArgs = @('-y','-f','gdigrab','-framerate','30','-offset_x',"$($bounds.X)",'-offset_y',"$($bounds.Y)",'-video_size',"$($bounds.Width)x$($bounds.Height)",'-draw_mouse','1','-i','desktop','-t',"$recordSec",'-c:v','libx264','-preset','veryfast','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',$rawVideo)
    & ffmpeg @ffArgs
    if ($LASTEXITCODE -ne 0) { throw "Recording failed" }
    Write-Host "[OK] Raw: $rawVideo" -ForegroundColor Green

    # Mux
    Write-Host '[..] Muxing with voiceover...' -ForegroundColor Yellow
    ffmpeg -y -i $rawVideo -i $VoiceMp3 -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 224k -shortest $FinalVideo
    if ($LASTEXITCODE -ne 0) { throw "Mux failed" }

    Write-Host "`n=== DONE: $FinalVideo ===" -ForegroundColor Green
} finally {
    # Cleanup
    $escaped = [Regex]::Escape($profDir)
    Get-CimInstance Win32_Process -Filter "Name = 'msedge.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine -match $escaped } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Get-Process msedge -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like '*Flamki*' } | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
    if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue }
    if (Test-Path $profDir) { Remove-Item -LiteralPath $profDir -Recurse -Force -ErrorAction SilentlyContinue }
}
