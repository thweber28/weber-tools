# cache-monitor
Zeigt über dem Prompt und in der Statuszeile: Ampel mit Cache-Countdown (1-Stunden-TTL; grün über 15 min, gelb 5 bis 15 min, rot unter 5 min oder kalt, auch ohne Daten), Kontext-Tokens, Kosten, Input/Output/Cache-Lesen/Cache-Schreiben des letzten Turns und als Summe der Sitzung. Annahme: die Sitzung nutzt 1-Stunden-Caching (bei 5-Minuten-TTL wäre die Ampel zu optimistisch). Ohne Einrichtung lauffähig; ccusage (npx ccusage) ergänzt die Rückschau.

Installation über Marketplace: `/plugin marketplace add <owner>/<repo>` und `/plugin install cache-monitor@weber-tools`.

## Statuszeile für ältere Claude-Code-Versionen
Versionen ohne Mod-Unterstützung laden das Plugin ohne Funktion. Dafür gibt es `statusline/cache-statusline.js` (Node.js): Ampel mit 1-h-Cache-Countdown, Tokens, Kosten. Einrichtung siehe Repository-README.
