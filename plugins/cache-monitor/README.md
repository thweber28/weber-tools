# cache-monitor
Zeigt über dem Prompt und in der Statuszeile: Ampel mit Cache-Countdown (1-Stunden-TTL; grün über 15 min, gelb 5 bis 15 min, rot unter 5 min oder kalt, auch ohne Daten), Kontext-Tokens, Kosten, Input/Output/Cache-Lesen/Cache-Schreiben des letzten Turns und als Summe der Sitzung. Annahme: die Sitzung nutzt 1-Stunden-Caching (bei 5-Minuten-TTL wäre die Ampel zu optimistisch). Ohne Einrichtung lauffähig; ccusage (npx ccusage) ergänzt die Rückschau.

Installation über Marketplace: `/plugin marketplace add <owner>/<repo>` und `/plugin install cache-monitor@weber-tools`.

## Statuszeile für ältere Claude-Code-Versionen
Versionen ohne Mod-Unterstützung laden das Plugin ohne Funktion. Dafür gibt es `statusline/cache-statusline.js` (Node.js): Ampel mit 1-h-Cache-Countdown, Tokens, Kosten. Einrichtung siehe Repository-README.

### Hinweise zur Anzeige
- Statuszeilen-Skript: Summen laufen über das ganze Transcript (je API-Antwort einmal, Subagenten eingeschlossen, passend zu den Kosten); die Cache-Uhr zählt nur den Hauptthread. Die Mod zählt ab ihrem Start. Ctx im Skript ist ein Näherungswert aus der letzten Antwort.
- Das Skript aktualisiert sich nur bei Claude-Code-Ereignissen; der Countdown tickt nicht von selbst. Die Mod aktualisiert alle 10 Sekunden.
- Bestätigt: Claude Code 2.1.220 lädt das Plugin ohne Fehler (ohne Funktion); Claude Code 2.1.310 im Terminal und `/cache` in der Desktop-App funktionieren.
