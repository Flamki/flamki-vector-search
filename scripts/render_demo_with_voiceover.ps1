param(
    [string]$Voiceover = 'recordings/demo_voiceover.mp3',
    [string]$FinalOutput = 'recordings/final_demo_with_voiceover.mp4',
    [string]$AudioDevice = 'Microphone Array (AMD Audio Device)'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $Voiceover)) {
    throw "Voiceover file not found: $Voiceover"
}

Write-Host 'Running endpoint preflight...'
python scripts/check_endpoints.py

$durationText = ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $Voiceover
$duration = [double]::Parse($durationText.Trim(), [System.Globalization.CultureInfo]::InvariantCulture)
$recordSec = [int][Math]::Ceiling($duration + 6)

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$raw = "recordings/raw_demo_$ts.mp4"

Write-Host "Voiceover duration: $duration sec"
Write-Host "Recording duration: $recordSec sec"
Write-Host "Raw recording: $raw"
Write-Host "Final output: $FinalOutput"

$seqCmd = "-ExecutionPolicy Bypass -File scripts/auto_demo_sequence.ps1 -TotalSec $recordSec"
Start-Process powershell -ArgumentList $seqCmd -WindowStyle Normal

Start-Sleep -Seconds 2
powershell -ExecutionPolicy Bypass -File scripts/record_demo_main_screen.ps1 -Output $raw -DurationSec $recordSec -AudioDevice $AudioDevice

ffmpeg -y -i $raw -i $Voiceover -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -shortest $FinalOutput

if ($LASTEXITCODE -ne 0) {
    throw "ffmpeg mux failed with exit code $LASTEXITCODE"
}

Write-Host "Done: $FinalOutput"
