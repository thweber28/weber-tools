# weber-tools
Claude-Code-Marketplace mit `cache-monitor`: Token-/Kostenanzeige und Cache-Countdown (1h TTL, Ampel grün/gelb/rot).

Installation (nach Veröffentlichung auf GitHub):
`/plugin marketplace add <owner>/<repo>` dann `/plugin install cache-monitor@weber-tools`

## Statuszeile (funktioniert ohne Mod-Unterstützung, Node.js nötig)
PowerShell:
```
$d = "$env:USERPROFILE\.claude"; New-Item -ItemType Directory -Force $d | Out-Null
Invoke-WebRequest https://raw.githubusercontent.com/thweber28/weber-tools/main/plugins/cache-monitor/statusline/cache-statusline.js -OutFile "$d\cache-statusline.js"
```
Dann in `%USERPROFILE%\.claude\settings.json` eintragen (Sicherungskopie vorher anlegen):
```
"statusLine": { "type": "command", "command": "node \"C:\\Users\\<NAME>\\.claude\\cache-statusline.js\"" }
```
