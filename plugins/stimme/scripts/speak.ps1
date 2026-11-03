# Spricht die Teile aus der Job-Datei mit den installierten Windows-Stimmen (System.Speech).
param([Parameter(Mandatory = $true)][string]$JobFile)
$ErrorActionPreference = 'Stop'
try {
  $job = Get-Content -Raw -Encoding UTF8 -LiteralPath $JobFile | ConvertFrom-Json
  Add-Type -AssemblyName System.Speech
  $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
  $s.Rate = [int]$job.rate
  $installed = @($s.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object { $_.VoiceInfo })
  $german = @($installed | Where-Object { $_.Culture.Name -like 'de*' })
  if ($german.Count -eq 0) { $german = $installed }
  $chosen = @{}
  # Zustand liegt in einer Hashtable, weil Event-Aktionen die Skript-Variablen nicht sicher sehen.
  $ctx = @{ idx = 0; job = $job }
  $write = {
    param($c, $pos, $len, $done)
    if (-not $c.job.stateFile) { return }
    $st = @{ id = 0; parts = @($c.job.parts); idx = $c.idx; pos = $pos; len = $len; done = $done } | ConvertTo-Json -Depth 4 -Compress
    $tmp = "$($c.job.stateFile).tmp"
    [IO.File]::WriteAllText($tmp, $st, (New-Object Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $tmp -Destination $c.job.stateFile -Force
  }
  $ctx.write = $write
  # Wortgrenzen der Stimme melden, damit das Untertitelfenster das aktuelle Wort hervorhebt.
  Register-ObjectEvent -InputObject $s -EventName SpeakProgress -SourceIdentifier stimme -MessageData $ctx -Action {
    $c = $Event.MessageData
    & $c.write $c $EventArgs.CharacterPosition $EventArgs.CharacterCount $false
  } | Out-Null
  foreach ($p in $job.parts) {
    $who = [string]$p.speaker
    if (-not $chosen.ContainsKey($who)) {
      $pick = $null
      foreach ($n in @($job.voices.$who)) {
        $pick = $german | Where-Object { $_.Name -like "*$n*" } | Select-Object -First 1
        if ($pick) { break }
      }
      if (-not $pick) { $pick = $german | Select-Object -First 1 }
      $chosen[$who] = $pick
    }
    $s.SelectVoice($chosen[$who].Name)
    # Gibt es nur eine deutsche Stimme, unterscheidet sich die Prüferin über das Tempo.
    $s.Rate = if ($who -eq 'pruefer' -and $german.Count -lt 2) { [int]$job.rate + 2 } else { [int]$job.rate }
    & $write $ctx -1 0 $false
    $null = $s.SpeakAsync([string]$p.text)
    while ($s.State -ne 'Ready') { Start-Sleep -Milliseconds 40 }
    $ctx.idx++
  }
  $ctx.idx = [Math]::Max(0, $ctx.idx - 1)
  & $write $ctx -1 0 $true
} finally {
  Remove-Item -LiteralPath $JobFile -ErrorAction SilentlyContinue
}
