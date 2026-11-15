#!/usr/bin/env python3
"""Erzeugt die Wohnflächenberechnung als Excel-Datei im Büro-Layout (Cockpit-Format).

Aufruf:  python wohnflaeche_xlsx.py eingabe.json ausgabe.xlsx
Eingabe: siehe ../examples/beispiel_eingabe.json (Maße in m, intern ungerundet, Anzeige 2 Nachkommastellen).
Alle Rechenwerte sind Excel-Formeln, damit die Berechnung nachprüfbar bleibt.
"""
import json
import sys
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

TITEL = {
    "WoFlV": "Wohnflächenberechnung nach der Wohnflächenverordnung (WoFlV vom 25.11.2003, BGBl. I S. 2346)",
    "II_BV_aF": "Wohnflächenberechnung nach der Zweiten Berechnungsverordnung (II. BV, Fassung bis 31.12.2003)",
    "DIN_277": "Flächenermittlung nach DIN 277:2021-08 (Netto-Raumfläche / Nutzungsfläche)",
}
FREISITZ_KOPF = {
    "WoFlV": "Balkone, Loggien, Dachgärten und Terrassen — § 2 Abs. 2 Nr. 2 und § 4 Nr. 4 WoFlV",
    "II_BV_aF": "Balkone, Loggien, Dachgärten und gedeckte Freisitze — § 44 Abs. 2 II. BV (a. F.)",
    "DIN_277": "Flächen mit Raumumschließung Sonderfall (S) — DIN 277:2021-08, 5.7.2",
}
FONT = "Arial"
BLAU, ORANGE, GRUEN = "DCE6F1", "FCE4D6", "E2EFDA"
dünn = Side(style="thin", color="808080")
KASTEN = Border(left=dünn, right=dünn, top=dünn, bottom=dünn)


def fill(farbe):
    return PatternFill("solid", fgColor=farbe)


def zelle(ws, ref, wert=None, fett=False, fmt=None, farbe=None, ausr=None, kursiv=False, rahmen=True):
    c = ws[ref]
    if wert is not None:
        c.value = wert
    c.font = Font(name=FONT, size=10, bold=fett, italic=kursiv)
    if fmt:
        c.number_format = fmt
    if farbe:
        c.fill = fill(farbe)
    if ausr:
        c.alignment = Alignment(horizontal=ausr, vertical="center", wrap_text=True)
    if rahmen:
        c.border = KASTEN
    return c


def blatt_name(w):
    name = f"{w['name']} - {w['geschoss']}"
    for z in "[]:*?/\\":
        name = name.replace(z, "")
    return name[:31]


def parameter_blatt(wb, d):
    ws = wb.active
    ws.title = "Parameter"
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 70
    putz = d.get("putzabzug", 0.03 if d.get("massart", "roh") == "roh" else 0.0)
    zeilen = [
        ("Projekt / Aktenzeichen", d.get("projekt", "")),
        ("Bauzustand (Plangrundlage)", d.get("bauzustand", "")),
        ("Regelwerk", d["regelwerk"]),
        ("Maßart", {"roh": "Rohbaumaße aus Bauzeichnung", "fertig": "Fertigmaße (lichte Maße)"}[d.get("massart", "roh")]),
        ("Putz- und Belagabzug", putz),
        ("Quelle der Maße", d.get("massquelle", "")),
        ("Datum", d.get("datum", "")),
    ]
    for i, (k, v) in enumerate(zeilen, start=1):
        zelle(ws, f"A{i}", k, fett=True, farbe=BLAU)
        zelle(ws, f"B{i}", v, fmt="0.0%" if k.startswith("Putz") else None, ausr="left")
    hinweise = [
        "Der pauschale Abzug für Putz und Belag ist ein Büro-Standard und kein Text der WoFlV. Die WoFlV rechnet mit lichten Maßen (§ 3 Abs. 1).",
        "Er entspricht der früheren Regel für Rohbaumaße (§ 43 Abs. 3 II. BV a. F.). Bei Fertigmaßen ist er 0 %.",
        "Berechnung auf Grundlage von Plänen, keine Ausmessung vor Ort. Bei abweichender Bauausführung neu ermitteln (§ 3 Abs. 4 WoFlV).",
    ]
    for i, h in enumerate(hinweise, start=len(zeilen) + 2):
        ws.merge_cells(f"A{i}:B{i}")
        zelle(ws, f"A{i}", h, kursiv=True, ausr="left", rahmen=False)
        ws.row_dimensions[i].height = 30
    return "Parameter!$B$5"


def wohnung_blatt(wb, w, d, putz_ref, titel, freisitz_kopf):
    ws = wb.create_sheet(blatt_name(w))
    for sp, br in zip("ABCDEFG", (34, 11, 11, 15, 10, 16, 56)):
        ws.column_dimensions[sp].width = br
    ws.merge_cells("A1:G1")
    zelle(ws, "A1", titel, fett=True, ausr="left")
    ws.merge_cells("A3:G3")
    zelle(ws, "A3", f"{w['name']} — Geschoss {w['geschoss']}", fett=True, farbe=BLAU, ausr="left")
    kopf = ["Raum / Teilfläche", "Länge [m]", "Breite [m]", "Grundfläche [m²]", "Faktor", "anrechenbar [m²]", "Anmerkung, lichte Höhe"]
    for sp, t in zip("ABCDEFG", kopf):
        zelle(ws, f"{sp}4", t, fett=True, farbe=BLAU, ausr="center")
    zeile = 5
    erste = zeile
    zeilen_info = []

    def raumzeile(r, z):
        zelle(ws, f"A{z}", r["name"])
        zelle(ws, f"B{z}", r.get("laenge"), fmt="0.00")
        zelle(ws, f"C{z}", r.get("breite"), fmt="0.00")
        zelle(ws, f"D{z}", f"=B{z}*C{z}", fmt="0.00")
        zelle(ws, f"E{z}", r.get("faktor", 1.0), fmt="0.00")
        zelle(ws, f"F{z}", f"=D{z}*E{z}", fmt="0.00")
        zelle(ws, f"G{z}", r.get("anmerkung", ""), ausr="left")
        zeilen_info.append((z, r["name"]))

    for r in w["raeume"]:
        raumzeile(r, zeile)
        zeile += 1
    letzte = zeile - 1
    zs, abz, nach = zeile, zeile + 1, zeile + 2
    zelle(ws, f"A{zs}", "Zwischensumme Räume", fett=True)
    for sp in "BCDE":
        zelle(ws, f"{sp}{zs}")
    zelle(ws, f"F{zs}", f"=SUM(F{erste}:F{letzte})", fett=True, fmt="0.00")
    zelle(ws, f"G{zs}")
    zelle(ws, f"A{abz}", "Abzug für Putz und Belag", fett=True)
    for sp in "BCD":
        zelle(ws, f"{sp}{abz}", farbe=ORANGE)
    zelle(ws, f"E{abz}", f"={putz_ref}", fmt="0.0%", farbe=ORANGE)
    zelle(ws, f"F{abz}", f"=-F{zs}*E{abz}", fmt="0.00", fett=True)
    zelle(ws, f"G{abz}", "Büro-Standard, siehe Blatt Parameter", kursiv=True, ausr="left")
    zelle(ws, f"A{nach}", "Grundfläche der Räume nach Abzug", fett=True)
    for sp in "BCDE":
        zelle(ws, f"{sp}{nach}")
    zelle(ws, f"F{nach}", f"=F{zs}+F{abz}", fett=True, fmt="0.00")
    zelle(ws, f"G{nach}")
    zeile = nach + 1
    ws.merge_cells(f"A{zeile}:G{zeile}")
    zelle(ws, f"A{zeile}", freisitz_kopf, fett=True, farbe=ORANGE, ausr="left")
    zeile += 1
    f_erste = zeile
    for r in w.get("freisitze", []) or [{"name": "", "laenge": None, "breite": None, "faktor": 0.25}]:
        raumzeile(r, zeile)
        zeile += 1
    f_letzte = zeile - 1
    fs = zeile
    zelle(ws, f"A{fs}", "Zwischensumme Freisitze (angerechnet)", fett=True)
    for sp in "BCDE":
        zelle(ws, f"{sp}{fs}")
    zelle(ws, f"F{fs}", f"=SUM(F{f_erste}:F{f_letzte})", fett=True, fmt="0.00")
    zelle(ws, f"G{fs}")
    wf = fs + 1
    zelle(ws, f"A{wf}", f"Wohnfläche {w['name']} nach {d['regelwerk'].replace('_', ' ')}", fett=True, farbe=GRUEN)
    for sp in "BCDE":
        zelle(ws, f"{sp}{wf}", farbe=GRUEN)
    zelle(ws, f"F{wf}", f"=F{nach}+F{fs}", fett=True, fmt="0.00", farbe=GRUEN)
    zelle(ws, f"G{wf}", farbe=GRUEN)
    ang, abw = wf + 1, wf + 2
    zelle(ws, f"A{ang}", "Angabe des Auftraggebers (ca.)")
    for sp in "BCDE":
        zelle(ws, f"{sp}{ang}")
    zelle(ws, f"F{ang}", w.get("angabe_auftraggeber"), fmt="0.00", farbe=ORANGE)
    zelle(ws, f"G{ang}", "Zahl aus der Auflistung des Auftraggebers", kursiv=True, ausr="left")
    zelle(ws, f"A{abw}", "Abweichung gegenüber der Angabe")
    for sp in "BCD":
        zelle(ws, f"{sp}{abw}")
    zelle(ws, f"E{abw}", f'=IF(F{ang}="","",F{wf}/F{ang}-1)', fmt="+0.0%;-0.0%")
    zelle(ws, f"F{abw}", f'=IF(F{ang}="","",F{wf}-F{ang})', fmt="+0.00;-0.00")
    zelle(ws, f"G{abw}", "Spalte E zeigt die Abweichung als Anteil der Angabe", kursiv=True, ausr="left")
    ws.freeze_panes = "A5"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    return ws.title, zeilen_info, wf


def main(eingabe, ausgabe):
    d = json.load(open(eingabe, encoding="utf-8"))
    regel = d["regelwerk"]
    wb = Workbook()
    putz_ref = parameter_blatt(wb, d)
    daten = []
    ws2 = wb.create_sheet("Übersicht")
    for sp, t in zip("ABC", ("Wohnung", "Geschoss", "Wohnfläche [m²]")):
        zelle(ws2, f"{sp}1", t, fett=True, farbe=BLAU, ausr="center")
    for sp, br in zip("ABC", (22, 12, 18)):
        ws2.column_dimensions[sp].width = br
    for i, w in enumerate(d["wohnungen"], start=2):
        name, info, wf = wohnung_blatt(wb, w, d, putz_ref, TITEL[regel], FREISITZ_KOPF[regel])
        daten.append((name, info, w))
        zelle(ws2, f"A{i}", w["name"])
        zelle(ws2, f"B{i}", w["geschoss"])
        zelle(ws2, f"C{i}", f"='{name}'!F{wf}", fmt="0.00", fett=True)
    ende = len(d["wohnungen"]) + 2
    zelle(ws2, f"A{ende}", "Summe", fett=True)
    zelle(ws2, f"B{ende}")
    zelle(ws2, f"C{ende}", f"=SUM(C2:C{ende - 1})", fmt="0.00", fett=True)
    ws = wb.create_sheet("Raumliste")
    kopf = ["Wohnung", "Geschoss", "Raum / Teilfläche", "Länge [m]", "Breite [m]", "Grundfläche [m²]", "Faktor", "anrechenbar [m²]"]
    for i, t in enumerate(kopf, start=1):
        zelle(ws, f"{get_column_letter(i)}1", t, fett=True, farbe=BLAU, ausr="center")
        ws.column_dimensions[get_column_letter(i)].width = [14, 10, 34, 11, 11, 16, 9, 16][i - 1]
    z = 2
    for blatt, info, w in daten:
        q = f"'{blatt}'!"
        for (zz, _name) in info:
            zelle(ws, f"A{z}", w["name"])
            zelle(ws, f"B{z}", w["geschoss"])
            zelle(ws, f"C{z}", f"={q}A{zz}")
            for sp, qs in zip("DEFGH", "BCDEF"):
                zelle(ws, f"{sp}{z}", f"={q}{qs}{zz}", fmt="0.00")
            z += 1
    ws.freeze_panes = "A2"
    wb.save(ausgabe)
    print(f"geschrieben: {ausgabe}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
