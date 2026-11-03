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
    $s.Speak([string]$p.text)
  }
} finally {
  Remove-Item -LiteralPath $JobFile -ErrorAction SilentlyContinue
}
