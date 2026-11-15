# Blender-Test mit einer realen Zeichnung (manuell, in Claude Desktop)

Dieser Test läuft nicht automatisch. Er braucht Claude Desktop mit laufendem Blender-MCP (Blender: Tab „MCP for Blender" → „Connected on localhost:9876"). Keine Kundendaten in dieses Protokoll schreiben.

## Vorbereitung
1. `.blend` speichern (z. B. `C:\Blender-projekte\test.blend`), Standardobjekte stehen lassen oder vorher Freigabe zum Löschen erteilen.
2. Neuen Chat in Claude Desktop öffnen. Prompt aus `references/blender-workflow.md` (= `Vorlagen/Textbausteine/Prompts/blender-3d-walkthrough.md`) einfügen.
3. Platzhalter füllen: `{{Bauzustand}}` = Plan und Datum des zu modellierenden Zustands (hier: Dachgeschossumbau 1996, EG und DG); `{{Ausgabemodus}}` = gutachterlich; `{{Projekt_Aktenzeichen}}` = TEST; `{{Ausgabepfad}}` = Testordner; `{{ffmpeg_Pfad}}` nur für den GIF-Test.
4. Zeichnungen als PDF anhängen (nur der Plan des gewählten Zustands).

## Erwartetes Verhalten (Abnahmekriterien)
| Nr. | Schritt | Erwartung | Ergebnis |
|---|---|---|---|
| 1 | Auswertung | Nennt Drehung/Lage der Pläne; Maßtabelle mit Fundstelle und „sicher/unsicher" | |
| 2 | Kettensummen | Prüft Teil- gegen Gesamtmaße (Toleranz ±5 mm); meldet Abweichungen als Rückfrage | |
| 3 | Lücken | Fragt fehlende Höhen, Dachform, Balkonmaße, Wandaufbauten ab; schätzt nicht | |
| 4 | Freigabe | Fasst zusammen und wartet auf „Go"; baut vorher nichts | |
| 5 | Szene | Fragt vor dem Löschen/Überschreiben; metrische Einheiten; Referenzbild kalibriert über bemaßte Strecke | |
| 6 | Modell | Bauteile einzeln, sprechend benannt, Collections je Geschoss | |
| 7 | Selbstcheck | bpy-Prüfskript mit Soll/Ist/Abweichung; Öffnungen über Kantenvertices, nicht über Bounding Box | |
| 8 | Vorschau | EEVEE-Vorschau ohne Speichern; Rechenzeit vor Endrender genannt | |
| 9 | Walkthrough | Kamera 1,65 m, Pfad ohne Wandkollision, Türen ≥ 0,9 m geprüft | |
| 10 | Modus | Einblendung „Veranschaulichung, ersetzt kein Aufmaß"; Schadensfarben nur auf Anweisung | |
| 11 | Export | Nur nach Freigabe, Zielpfad genannt, MP4 und GIF mit Dateigröße | |

## Auswertung
- Abweichungen vom Erwarteten mit Schrittnummer festhalten und im Chat mit Claude Code besprechen.
- Besonders prüfen: Werden unsichere Handschrift-Maße als Rückfrage behandelt? Werden die Pläne aus 1971 und 1996 verwechselt? Stimmen Geschosshöhen mit den bestätigten Angaben überein?
- ImmoScout24-Test nur im Modus „Anzeige": Standbilder 4:3 ohne Text im Bild, Kennzeichnung in der Bildbeschreibung, Video ≤ 1 GB.
