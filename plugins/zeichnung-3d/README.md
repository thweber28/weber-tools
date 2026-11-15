# zeichnung-3d

Claude-Skill: aus bemaßten Bauzeichnungen Maßtabelle, Wohnflächenberechnung (Excel im Büro-Layout), maßgenaues Blender-3D-Modell sowie Bilder und Walkthrough (MP4/GIF).

Installation: `/plugin marketplace add thweber28/weber-tools`, dann `/plugin install zeichnung-3d@weber-tools`.

Voraussetzungen: Python 3 mit `openpyxl` (Excel-Ausgabe), Blender mit MCP-Verbindung (3D-Teil), lokal installiertes `ffmpeg` (nur für GIF), LibreOffice (nur für die Tests).

Einstieg: `skills/zeichnung-3d/SKILL.md`. Tests: `python skills/zeichnung-3d/tests/run_tests.py` (LibreOffice nötig).

Status: Entwurf. Zwei unabhängige Prüfer-Läufe (je Gelb) eingearbeitet. Noch nicht getestet: Blender-Teil in der Praxis, Cockpit-Import der Excel-Datei, Word-Tabelle (gibt es nicht als Skript). ImmoScout24-Angaben sind Stand 2026-11-15 und vor dem Upload zu prüfen.

`blender-workflow.md` ist eine Kopie von `Vorlagen/Textbausteine/Prompts/blender-3d-walkthrough.md`; ein Test prüft, dass beide identisch bleiben.
