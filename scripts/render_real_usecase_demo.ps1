param(
    [string]$VoiceText = 'DEMO_TELEPROMPTER_REAL_USECASE.txt',
    [string]$VoiceMp3 = 'recordings/demo_voiceover_real_usecase.mp3',
    [string]$RawVideo = '',
    [string]$FinalVideo = 'recordings/final_demo_real_usecase.mp4',
    [string]$VoiceId = 'JBFqnCBsd6RMkjVDRZzb',
    [switch]$SkipVoiceGeneration,
    [int]$DurationOverrideSec = 0
)

$ErrorActionPreference = 'Stop'

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSec = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { return $true }
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Get-VoiceDuration {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        throw "Voice file not found: $Path"
    }

    $d = ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $Path
    return [double]::Parse($d.Trim(), [System.Globalization.CultureInfo]::InvariantCulture)
}

function Get-PrimaryBounds {
    Add-Type -AssemblyName System.Windows.Forms
    return [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
}

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class WinApi {
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@

function Minimize-AllWindows {
    try {
        $shell = New-Object -ComObject Shell.Application
        $shell.MinimizeAll() | Out-Null
    } catch {}
}

function Maximize-DemoWindow {
    param([int]$TimeoutSec = 20)

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $bounds = Get-PrimaryBounds
    $wShell = New-Object -ComObject WScript.Shell

    while ((Get-Date) -lt $deadline) {
        $p = Get-Process msedge -ErrorAction SilentlyContinue | Where-Object {
            $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like '*Flamki Demo Showcase*'
        } | Select-Object -First 1

        if ($p) {
            [WinApi]::ShowWindow($p.MainWindowHandle, 3) | Out-Null
            [WinApi]::SetWindowPos($p.MainWindowHandle, [IntPtr](-1), $bounds.X, $bounds.Y, $bounds.Width, $bounds.Height, 0x0040) | Out-Null
            [WinApi]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
            $null = $wShell.AppActivate($p.Id)
            return $true
        }

        Start-Sleep -Milliseconds 500
    }

    return $false
}

function Close-ExistingDemoWindow {
    $wins = Get-Process msedge -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like '*Flamki Demo Showcase*'
    }

    foreach ($w in $wins) {
        try { Stop-Process -Id $w.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
}

function Stop-DemoEdgeByProfile {
    param([string]$ProfileDir)

    if ([string]::IsNullOrWhiteSpace($ProfileDir)) { return }
    $escaped = [Regex]::Escape($ProfileDir)
    $procs = Get-CimInstance Win32_Process -Filter "Name = 'msedge.exe'" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and $_.CommandLine -match $escaped
    }
    foreach ($p in $procs) {
        try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
    }
}

Write-Host 'Running endpoint preflight...'
python scripts/check_endpoints.py

$serverProc = $null
$edgeProc = $null
$demoProfileDir = ''

try {
    Write-Host 'Starting local showcase server on :8787 ...'
    $serverProc = Start-Process python -ArgumentList '-m','http.server','8787','--bind','127.0.0.1' -WorkingDirectory (Get-Location).Path -PassThru -WindowStyle Hidden

    if (-not (Wait-HttpOk -Url 'http://127.0.0.1:8787/scripts/demo_showcase/index.html' -TimeoutSec 20)) {
        throw 'Showcase page did not start on http://127.0.0.1:8787'
    }

    if (-not $SkipVoiceGeneration) {
        if (-not $env:ELEVENLABS_API_KEY) {
            throw 'ELEVENLABS_API_KEY is not set. Provide it or use -SkipVoiceGeneration with an existing voice file.'
        }

        try {
            Write-Host 'Generating ElevenLabs voiceover...'
            python scripts/generate_elevenlabs_voiceover.py --text-file $VoiceText --output $VoiceMp3 --voice-id $VoiceId --speaker-boost
            if ($LASTEXITCODE -ne 0) {
                throw "Voice generation failed with exit code $LASTEXITCODE"
            }
        } catch {
            if (Test-Path $VoiceMp3) {
                Write-Warning "Voice generation failed; using existing voice file: $VoiceMp3"
            } else {
                throw
            }
        }
    } elseif (-not (Test-Path $VoiceMp3)) {
        throw "SkipVoiceGeneration is set, but voice file does not exist: $VoiceMp3"
    }

    $voiceSec = Get-VoiceDuration -Path $VoiceMp3
    $recordSec = if ($DurationOverrideSec -gt 0) { $DurationOverrideSec } else { [int][Math]::Ceiling($voiceSec + 4) }

    if ([string]::IsNullOrWhiteSpace($RawVideo)) {
        $RawVideo = "recordings/raw_real_usecase_$(Get-Date -Format 'yyyyMMdd_HHmmss').mp4"
    }

    Write-Host "Voiceover duration: $([Math]::Round($voiceSec,2)) sec"
    Write-Host "Recording duration: $recordSec sec"
    Write-Host "Raw video: $RawVideo"
    Write-Host "Final video: $FinalVideo"

    Close-ExistingDemoWindow
    Minimize-AllWindows
    $demoProfileDir = Join-Path $env:TEMP ("flamki_demo_profile_" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $demoProfileDir | Out-Null
    Write-Host 'Opening showcase in dedicated Microsoft Edge window...'
    $edgeProc = Start-Process msedge -ArgumentList "--user-data-dir=$demoProfileDir",'--no-first-run','--disable-gpu','--app=http://127.0.0.1:8787/scripts/demo_showcase/index.html' -PassThru

    if (-not (Maximize-DemoWindow -TimeoutSec 20)) {
        Write-Warning 'Could not reliably detect showcase window title; recording primary desktop anyway.'
    }

    Start-Sleep -Seconds 2
    Write-Host 'Recording primary monitor area...'
    $bounds = Get-PrimaryBounds

    $ffArgs = @(
        '-y',
        '-f','gdigrab',
        '-framerate','30',
        '-offset_x',"$($bounds.X)",
        '-offset_y',"$($bounds.Y)",
        '-video_size',"$($bounds.Width)x$($bounds.Height)",
        '-draw_mouse','1',
        '-i','desktop',
        '-t',"$recordSec",
        '-c:v','libx264',
        '-preset','veryfast',
        '-crf','16',
        '-pix_fmt','yuv420p',
        '-movflags','+faststart',
        $RawVideo
    )

    & ffmpeg @ffArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Screen recording failed with ffmpeg exit code $LASTEXITCODE"
    }

    Write-Host 'Muxing high-quality voiceover...'
    ffmpeg -y -i $RawVideo -i $VoiceMp3 -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 224k -shortest $FinalVideo
    if ($LASTEXITCODE -ne 0) {
        throw "Muxing failed with ffmpeg exit code $LASTEXITCODE"
    }

    Stop-DemoEdgeByProfile -ProfileDir $demoProfileDir
    Close-ExistingDemoWindow
    Write-Host "Done: $FinalVideo"
}
finally {
    Stop-DemoEdgeByProfile -ProfileDir $demoProfileDir
    Close-ExistingDemoWindow
    if ($serverProc -and -not $serverProc.HasExited) {
        Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue
    }
    if ($demoProfileDir -and (Test-Path $demoProfileDir)) {
        Remove-Item -LiteralPath $demoProfileDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
