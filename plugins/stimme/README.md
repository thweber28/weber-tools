# stimme
Claude Code spricht am Ende jeder Antwort eine kurze Sprechzeile (🔊). Windows-Systemstimme (System.Speech, kostenlos, offline), Node.js nötig. Basis: Setup aus dem Video "Claude Code mit Stimme" (Fish Audio), hier ohne Fish und ohne Regieanweisungen.

Installation: `/plugin marketplace add thweber28/weber-tools` dann `/plugin install stimme@weber-tools`, Claude Code neu starten.

- Nach jeder Antwort wird die 🔊-Zeile gesprochen. Eine neue Nachricht stoppt die Stimme sofort.
- Freigabe-Fragen und Leerlauf werden kurz angesagt.
- Agent `stimme:pruefer`: zweite Stimme (Dialog `🔊 Prüfer: …` / `🔊 Claude: …`).
- Die Sprechregel kommt per SessionStart-Hook, keine CLAUDE.md nötig.

Stimmen: Standard sind Microsoft Stefan/Hedda/Katja (Windows-Sprachpaket Deutsch). Eigene Werte in `%USERPROFILE%\.claude\stimme.json`, z. B. `{ "rate": 1, "voices": { "claude": ["Hedda"], "pruefer": ["Katja"] } }`. Installierte Stimmen: `Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices().VoiceInfo.Name`.

Grenzen: Gesprochen wird nur, wenn Hooks laufen (Claude Code lokal im Terminal, nicht in Cloud-Sitzungen). Die Systemstimme kann keine Emotionen; Regieanweisungen in [..] werden entfernt. Prüfen ohne Ton: `echo {"last_assistant_message":"🔊 Test."} | set STIMME_DRYRUN=1 && node scripts\stop-hook.js`.
