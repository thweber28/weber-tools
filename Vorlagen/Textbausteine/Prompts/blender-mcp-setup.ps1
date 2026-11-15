# Blender-MCP-Einrichtung (Windows, PowerShell)
# Quelle: PyPI "mcp-for-blender" (frueher "blender-mcp"), Maintainer Siddharth Ahuja, MIT-Lizenz.
# Jeder Schritt fragt vorher nach. Es wird nichts ohne Bestaetigung installiert oder geaendert.
# Aufruf:  powershell -ExecutionPolicy Bypass -File .\blender-mcp-setup.ps1 [-SafeMode] [-Telemetrie]

param(
    [switch]$SafeMode,    # setzt BLENDER_MCP_SAFE_MODE=1 (blockiert riskanten Code, kann Skripte einschraenken)
    [switch]$Telemetrie   # Standard: Telemetrie AUS (DISABLE_TELEMETRY=true). Mit Schalter bleibt sie an.
)

function Frage($text) {
    $a = Read-Host "$text [j/N]"
    return ($a -match '^(j|y)')
}

Write-Host "`n== 1. Voraussetzungen pruefen ==" -ForegroundColor Cyan
$hasWinget = [bool](Get-Command winget -ErrorAction SilentlyContinue)
$hasUv     = [bool](Get-Command uv -ErrorAction SilentlyContinue)
$blenderExe = Get-ChildItem "$env:ProgramFiles\Blender Foundation" -Filter blender.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
Write-Host "winget: $hasWinget | uv: $hasUv | Blender: $([bool]$blenderExe)"
if (-not $hasWinget -and (-not $hasUv -or -not $blenderExe)) {
    Write-Host "winget fehlt. Bitte uv (https://docs.astral.sh/uv/) und Blender (https://www.blender.org/download/) manuell installieren und das Skript erneut starten." -ForegroundColor Yellow
    exit 1
}

Write-Host "`n== 2. Blender installieren ==" -ForegroundColor Cyan
if ($blenderExe) { Write-Host "Blender gefunden: $($blenderExe.FullName)" }
elseif (Frage "Blender (Blender Foundation) per winget installieren?") {
    winget install --id BlenderFoundation.Blender -e
} else { Write-Host "Uebersprungen." }

Write-Host "`n== 3. uv installieren ==" -ForegroundColor Cyan
if ($hasUv) { Write-Host "uv vorhanden." }
elseif (Frage "uv (astral-sh.uv) per winget installieren? (NICHT per pip)") {
    winget install --id=astral-sh.uv -e
    Write-Host "Bitte neues PowerShell-Fenster oeffnen und das Skript erneut starten, damit uv im PATH ist." -ForegroundColor Yellow
    exit 0
} else { Write-Host "Uebersprungen. Ohne uv geht es nicht weiter."; exit 1 }

Write-Host "`n== 4. Blender-Add-on installieren ==" -ForegroundColor Cyan
if (Frage "'uvx mcp-for-blender install-addon' ausfuehren (laedt Paket von PyPI und kopiert das Add-on in den Blender-Addon-Ordner)?") {
    uvx mcp-for-blender install-addon
} else { Write-Host "Uebersprungen." }

Write-Host "`n== 5. Claude-Desktop-Konfiguration ==" -ForegroundColor Cyan
$kandidaten = @(
    "$env:APPDATA\Claude\claude_desktop_config.json"
) + (Get-ChildItem "$env:LOCALAPPDATA\Packages" -Filter "Claude_*" -ErrorAction SilentlyContinue |
     ForEach-Object { Join-Path $_.FullName "LocalCache\Roaming\Claude\claude_desktop_config.json" })
$cfg = $kandidaten | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $cfg) { $cfg = $kandidaten[0] }
Write-Host "Konfigurationsdatei: $cfg"

$umgebung = @{}
if (-not $Telemetrie) { $umgebung["DISABLE_TELEMETRY"] = "true" }
if ($SafeMode)        { $umgebung["BLENDER_MCP_SAFE_MODE"] = "1" }
$eintrag = [ordered]@{ command = "cmd"; args = @("/c","uvx","mcp-for-blender") }
if ($umgebung.Count -gt 0) { $eintrag["env"] = $umgebung }

if (Frage "Eintrag 'blender' in die Konfiguration schreiben (Sicherung als .bak wird angelegt)?") {
    if (Test-Path $cfg) {
        Copy-Item $cfg "$cfg.bak" -Force
        $json = Get-Content $cfg -Raw | ConvertFrom-Json
    } else {
        New-Item -ItemType Directory -Force (Split-Path $cfg) | Out-Null
        $json = [pscustomobject]@{}
    }
    if (-not $json.PSObject.Properties["mcpServers"]) {
        $json | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([pscustomobject]@{})
    }
    $json.mcpServers | Add-Member -NotePropertyName blender -NotePropertyValue ([pscustomobject]$eintrag) -Force
    $json | ConvertTo-Json -Depth 10 | Set-Content $cfg -Encoding UTF8
    Write-Host "Geschrieben. Sicherung: $cfg.bak"
} else { Write-Host "Uebersprungen." }

Write-Host "`n== 6. Letzte Schritte (manuell) ==" -ForegroundColor Cyan
@"
1. Claude Desktop ueber das Tray-Symbol VOLLSTAENDIG beenden und neu starten.
2. Blender starten: Edit > Preferences > Add-ons > 'Interface: MCP for Blender' aktivieren.
3. 3D-Viewport: Taste N > Tab 'MCP for Blender' > 'Start MCP Server' (Port 9876, nur localhost).
4. In Claude Desktop pruefen, ob der Server 'blender' erscheint. Test: 'Erstelle einen Wuerfel 1 m x 1 m x 1 m.'

Hinweise: Der Socket hat keine Authentifizierung - Port 9876 nicht freigeben/weiterleiten.
'execute_blender_code' fuehrt beliebigen Python-Code aus: .blend vorher speichern.
Nur EINE MCP-Instanz gleichzeitig (nicht Claude Desktop und Cursor).
"@ | Write-Host
