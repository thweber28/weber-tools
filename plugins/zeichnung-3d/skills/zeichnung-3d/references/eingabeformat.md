# Eingabeformat für `scripts/wohnflaeche_xlsx.py`

Aufruf: `python scripts/wohnflaeche_xlsx.py eingabe.json ausgabe.xlsx` (Voraussetzung: `pip install openpyxl`). Beispiel: `examples/beispiel_eingabe.json`. Tests: `python tests/run_tests.py` (benötigt LibreOffice `soffice`).

| Feld | Pflicht | Bedeutung |
|---|---|---|
| `regelwerk` | ja | `WoFlV`, `II_BV_aF` oder `DIN_277` |
| `massart` | nein (Standard `roh`) | `roh` (Abzug 3 %, Büro-Standard) oder `fertig` (Abzug immer 0 %) |
| `putzabzug` | nein | Überschreibt 3 % nur bei `roh`. Bei `fertig` und `DIN_277` wirkungslos |
| `projekt`, `bauzustand`, `massquelle`, `datum` | nein | Erscheinen im Blatt „Parameter" |
| `wohnungen[]` | ja | Je Wohnung: `name`, `geschoss` (Kombination eindeutig, Blattname ≤ 31 Zeichen) |
| `raeume[]` | ja | `name`, `laenge`, `breite` (m, > 0), `faktor` (0 bis 1, Standard 1), `anmerkung` |
| `freisitze[]` | nein | wie Räume, aber `faktor` **Pflicht** (Regelfall 0,25, höchstens 0,5, begründen). Bei `DIN_277` Faktor 1 |
| `angabe_auftraggeber` | nein | Zahl > 0 aus der Auflistung des Auftraggebers; ergibt die Abweichungszeile |

Verhalten: Fehlende oder ungültige Angaben führen zum Abbruch mit Klartext (`FEHLER: …`). Es wird nichts geschätzt. Beträge sind `ROUND(…,3)`, Anzeige mit 2 Nachkommastellen. Texte werden nie als Formeln gespeichert.
