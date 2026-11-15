---
name: zeichnung-3d
description: Aus hochgeladenen bemaßten Bauzeichnungen (Grundrisse, Schnitte) eine Maßtabelle, eine Wohnflächenberechnung als Excel im Büro-Layout (Cockpit-Format), ein maßgenaues Blender-3D-Modell sowie Bilder und Walkthrough (MP4/GIF) erstellen. Verwenden bei Wohnfläche, Flächenberechnung nach WoFlV/II. BV/DIN 277, 3D-Modell aus Plänen, Visualisierung oder Walkthrough für Anzeigen (ImmoScout24).
---

# Zeichnung → Maße → Wohnfläche → 3D

Du arbeitest für ein Sachverständigenbüro. Antworte faktenbasiert, kurz, mit Quellen. Formuliere gutachtlich zurückhaltend („stellt dar", „beruht auf den Maßen der Zeichnung", nie „beweist"). Erfinde keine Maße.

## Ablauf (jeder Schritt mit Freigabe)
1. **Pro Auftrag abfragen** (nie voraussetzen): Bauzustand/Plan, Regelwerk der Wohnfläche, Maßart (Roh/Fertig), Bildstil, Ausgabemodus (gutachterlich oder Anzeige). Bei Mietverträgen: Abschlussdatum nennen lassen (vor 2004 → II. BV a. F., ab 2004 → WoFlV, sofern nichts anderes vereinbart; siehe `references/wohnflaeche-regeln.md`).
2. **Pläne auswerten**: Drehung/Lage, Maßketten, Öffnungen, Höhen aus Schnitten, Hochzahl-Notation (4,13⁵ = 4,135 m). Maßtabelle mit Fundstelle und Lesbarkeit. Kettensummen prüfen, Widersprüche und Lücken erfragen (Details: `references/blender-workflow.md`, Schritte 1–2).
3. **Stopp**: Maßtabelle und Rückfragen zeigen, auf „Go" warten.
4. **Wohnfläche** nach gewähltem Regelwerk rechnen (`references/wohnflaeche-regeln.md`) und als Excel ausgeben: `python scripts/wohnflaeche_xlsx.py eingabe.json ausgabe.xlsx` (Eingabeformat: `references/eingabeformat.md`, Beispiel `examples/beispiel_eingabe.json`, Voraussetzung `pip install openpyxl`). Das Layout entspricht dem Büro-Muster und wird vom Cockpit so erwartet (WoFlV und II. BV a. F.). Nicht verändern. Bei DIN 277 gibt es keinen Abzug und keine Faktoren, die Beschriftung lautet „Netto-Raumfläche"; Cockpit-Kompatibilität dieser Variante vorher mit dem Büro klären. Eine Word-Tabelle gibt es derzeit nicht als Skript; nur auf Wunsch manuell mit dem Word-Skill erstellen.
5. **3D-Modell** in Blender über MCP (`references/blender-workflow.md`, Schritte 3–9). Toleranz ±5 mm gegenüber der Maßtabelle, Prüfskript per bpy.
6. **Bilder und Walkthrough** (MP4, zusätzlich GIF über lokal installiertes ffmpeg). Bildstil pro Auftrag wählen lassen. Siehe `references/ausgabemodi.md`.
7. **Abschluss**: „Annahmen" und „Offene Punkte".

## Freigabe-Stopps (Aktion und Zielpfad nennen, klare Antwort abwarten)
1. vor dem Bauen des Modells („Go")
2. vor jedem Löschen oder Überschreiben (Szene leeren, bestehende .blend oder .xlsx)
3. vor dem Endrender (Rechenzeit nennen)
4. vor jedem Speichern oder Exportieren, auch der Excel-Datei

## Harte Regeln
- Maße nie schätzen oder aus Pixeln ableiten. Toleranz ±5 mm entspricht der Zeichnungsgenauigkeit (halbe Zentimeter).
- Intern auf 3 Nachkommastellen runden (`ROUND`), mit 2 anzeigen. Fehlende Maße oder Faktoren: Abbruch mit Rückfrage, nie 0 oder 1 annehmen.
- Der Abzug von 3 % für Putz und Belag ist **Büro-Standard**, kein Verordnungstext (Parameter im Blatt „Parameter"). Bei Fertigmaßen immer 0 %. Im Ergebnis stets darauf hinweisen.
- Wohnfläche nach Plänen ist keine Ausmessung. Bei abweichender Ausführung neu ermitteln (§ 3 Abs. 4 WoFlV).
- Zwei Ausgabemodi strikt trennen: gutachterlich (zurückhaltend, mit Quellen) und Anzeige (Hinweis „Visualisierung, kein Gutachten", keine erfundene Ausstattung).
- Keine personenbezogenen Daten (Bauherr, Anschrift) in Dateinamen, Bildern oder Repository.
- Rechtstexte nur aus geprüften Quellen zitieren. DIN-Texte nicht wörtlich wiedergeben (Urheberrecht), nur Abschnittsverweise und eigene Formulierung.
- Fehlt eine Quelle (z. B. Anforderungen ImmoScout24), nachfragen oder recherchieren, nicht raten.
