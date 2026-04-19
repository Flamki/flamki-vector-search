param(
    [string]$Output = "recordings/demo_$(Get-Date -Format 'yyyyMMdd_HHmmss').mp4",
    [int]$DurationSec = 240,
    [string]$AudioDevice = "Microphone Array (AMD Audio Device)",
    [int]$Fps = 30
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    throw 'ffmpeg not found in PATH.'
}

Add-Type -AssemblyName System.Windows.Forms
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$width = $bounds.Width
$height = $bounds.Height
$offsetX = $bounds.X
$offsetY = $bounds.Y

$outPath = [System.IO.Path]::GetFullPath($Output)
$outDir = Split-Path -Parent $outPath
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir | Out-Null
}

Write-Host "Recording primary screen only: ${width}x${height} at (${offsetX},${offsetY})"
Write-Host "Audio device: $AudioDevice"
Write-Host "Output: $outPath"
Write-Host "Duration: $DurationSec sec"

$ffArgs = @(
    '-y',
    '-f', 'gdigrab',
    '-framerate', "$Fps",
    '-offset_x', "$offsetX",
    '-offset_y', "$offsetY",
    '-video_size', "${width}x${height}",
    '-draw_mouse', '1',
    '-i', 'desktop',
    '-f', 'dshow',
    '-i', "audio=$AudioDevice",
    '-t', "$DurationSec",
    '-c:v', 'libx264',
    '-preset', 'veryfast',
    '-crf', '22',
    '-pix_fmt', 'yuv420p',
    '-c:a', 'aac',
    '-b:a', '160k',
    '-movflags', '+faststart',
    $outPath
)

& ffmpeg @ffArgs

if ($LASTEXITCODE -ne 0) {
    throw "ffmpeg failed with exit code $LASTEXITCODE"
}

Write-Host "Recording complete: $outPath"
