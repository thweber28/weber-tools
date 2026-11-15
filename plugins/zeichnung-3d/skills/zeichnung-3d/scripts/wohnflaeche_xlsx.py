#!/usr/bin/env python3
"""Erzeugt die Wohnflächenberechnung als Excel-Datei im Büro-Layout (Cockpit-Format).

Aufruf:  python wohnflaeche_xlsx.py eingabe.json ausgabe.xlsx [--ueberschreiben] [--mit-werten]
Voraussetzung: pip install openpyxl
  --ueberschreiben  Zieldatei darf ersetzt werden (sonst Abbruch, wenn sie existiert)
  --mit-werten      rechnet die Formeln mit LibreOffice (soffice) neu und speichert die Ergebnisse
                    in der Datei, falls das Cockpit Werte ohne Neuberechnung liest
Eingabeformat: references/eingabeformat.md, Beispiel: examples/beispiel_eingabe.json
Maße in m, intern auf 3 Nachkommastellen gerundet (ROUND), Anzeige mit 2 Nachkommastellen.
Alle Rechenwerte sind Excel-Formeln, damit die Berechnung nachprüfbar bleibt.
Fehlende oder ungültige Eingaben führen zum Abbruch mit Klartext (nichts wird geschätzt).
"""
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

REGELWERKE = {
    "WoFlV": {
        "titel": "Wohnflächenberechnung nach der Wohnflächenverordnung (WoFlV vom 25.11.2003, BGBl. I S. 2346)",
        "freisitz": "Balkone, Loggien, Dachgärten und Terrassen — § 2 Abs. 2 Nr. 2 und § 4 Nr. 4 WoFlV",
        "ende": "Wohnfläche {w} nach WoFlV",
        "faktor_max": 0.5,
        "abzug": True,
        "hinweise": [
            "Der pauschale Abzug für Putz und Belag ist ein Büro-Standard und kein Text der WoFlV. Die WoFlV rechnet mit lichten Maßen (§ 3 Abs. 1).",
            "Er entspricht der früheren Regel für Rohbaumaße (§ 43 Abs. 3 II. BV a. F.). Bei Fertigmaßen ist er 0 %.",
        ],
    },
    "II_BV_aF": {
        "titel": "Wohnflächenberechnung nach der Zweiten Berechnungsverordnung (II. BV, Fassung bis 31.12.2003)",
        "freisitz": "Balkone, Loggien, Dachgärten und gedeckte Freisitze — § 44 Abs. 2 II. BV (a. F.)",
        "ende": "Wohnfläche {w} nach II. BV (a. F.)",
        "faktor_max": 0.5,
        "abzug": True,
        "hinweise": [
            "Kürzung um 3 vom Hundert bei Rohbaumaßen: § 43 Abs. 3 II. BV a. F. (Wortlaut-Abdruck im Info 06/2018 des Berliner Mietervereins, Sekundärquelle).",
            "Die Altfassung der II. BV (bis 31.12.2003) liegt amtlich nicht vor. Bei Fertigmaßen entfällt die Kürzung.",
        ],
    },
    "DIN_277": {
        "titel": "Flächenermittlung nach DIN 277:2021-08 (Netto-Raumfläche, keine Wohnfläche im Sinne der WoFlV)",
        "freisitz": "Flächen mit Raumumschließung Sonderfall (S) — DIN 277:2021-08, 5.7.2",
        "ende": "Netto-Raumfläche {w} nach DIN 277",
        "faktor_max": 1.0,
        "abzug": False,
        "hinweise": [
            "DIN 277 kennt keine Anrechnungsfaktoren und keinen Putzabzug; Flächen sind nach lichten Maßen zu ermitteln (6.2).",
            "Die Norm nimmt keine Bewertung vor. Eine Wohnfläche im Sinne der WoFlV ergibt sich daraus nicht.",
        ],
    },
}
HINWEIS_PLAN = ("Berechnung auf Grundlage von Plänen, keine Ausmessung vor Ort. Die Bauzeichnung muss für ein bauordnungsrechtliches Verfahren gefertigt oder dafür geeignet sein und die Ermittlung der lichten Maße ermöglichen; bei abweichender Bauausführung ist neu zu ermitteln (§ 3 Abs. 4 WoFlV).")
MAX_MASS = 1000.0  # m, Plausibilitätsgrenze
FONT = "Arial"
BLAU, ORANGE, GRUEN = "DCE6F1", "FCE4D6", "E2EFDA"
_d = Side(style="thin", color="808080")
KASTEN = Border(left=_d, right=_d, top=_d, bottom=_d)


class Eingabefehler(Exception):
    pass


def zahl(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def pruefe(d):
    """Validiert die Eingabe. Bricht mit Klartext ab, schätzt nichts. Gibt Warnungen zurück."""
    warn = []
    if not isinstance(d, dict):
        raise Eingabefehler("Wurzel der JSON-Datei muss ein Objekt sein")
    if d.get("regelwerk") not in REGELWERKE:
        raise Eingabefehler(f"regelwerk muss eines von {list(REGELWERKE)} sein, nicht {d.get('regelwerk')!r}")
    if d.get("massart", "roh") not in ("roh", "fertig"):
        raise Eingabefehler("massart muss 'roh' oder 'fertig' sein")
    if "putzabzug" in d and not (zahl(d["putzabzug"]) and 0 <= d["putzabzug"] <= 0.1):
        raise Eingabefehler("putzabzug muss eine Zahl von 0 bis 0,1 sein (z. B. 0,03)")
    if "pauschalabzug_44_abs3" in d:
        if d["regelwerk"] != "II_BV_aF":
            raise Eingabefehler("pauschalabzug_44_abs3 gibt es nur beim Regelwerk II_BV_aF")
        if not (zahl(d["pauschalabzug_44_abs3"]) and 0 <= d["pauschalabzug_44_abs3"] <= 0.1):
            raise Eingabefehler("pauschalabzug_44_abs3 muss eine Zahl von 0 bis 0,1 sein")
    if not isinstance(d.get("wohnungen"), list) or not d["wohnungen"]:
        raise Eingabefehler("wohnungen fehlt oder ist leer")
    fmax = REGELWERKE[d["regelwerk"]]["faktor_max"]
    gesehen = set()
    for w in d["wohnungen"]:
        if not isinstance(w, dict):
            raise Eingabefehler("jede Wohnung muss ein Objekt sein")
        for k in ("name", "geschoss"):
            if not str(w.get(k, "")).strip():
                raise Eingabefehler(f"Wohnung ohne {k}")
        schluessel = (str(w["name"]).strip().lower(), str(w["geschoss"]).strip().lower())
        if schluessel in gesehen:
            raise Eingabefehler(f"Wohnung/Geschoss doppelt: {w['name']} / {w['geschoss']}. Bitte eindeutig benennen.")
        gesehen.add(schluessel)
        if not isinstance(w.get("raeume"), list) or not w["raeume"]:
            raise Eingabefehler(f"{w['name']}: keine Räume angegeben")
        if w.get("freisitze") is not None and not isinstance(w["freisitze"], list):
            raise Eingabefehler(f"{w['name']}: freisitze muss eine Liste sein")
        for art, liste in (("Raum", w["raeume"]), ("Freisitz", w.get("freisitze") or [])):
            for r in liste:
                if not isinstance(r, dict):
                    raise Eingabefehler(f"{w['name']}: jeder {art} muss ein Objekt sein")
                ort = f"{w['name']} / {art} {r.get('name', '?')!r}"
                if not str(r.get("name", "")).strip():
                    raise Eingabefehler(f"{ort}: Name fehlt")
                for k in ("laenge", "breite"):
                    v = r.get(k)
                    if not zahl(v) or not (0 < v <= MAX_MASS):
                        raise Eingabefehler(f"{ort}: {k} fehlt oder liegt nicht in 0 bis {MAX_MASS:g} m (Maße werden nie geschätzt)")
                if "faktor" in r and r["faktor"] is None:
                    raise Eingabefehler(f"{ort}: faktor ist null (angeben oder weglassen)")
                f = r.get("faktor")
                if art == "Freisitz" and f is None:
                    raise Eingabefehler(f"{ort}: faktor fehlt (Regelfall WoFlV 0,25, begründen)")
                f = 1.0 if f is None else f
                if not zahl(f) or not (0 <= f <= (fmax if art == "Freisitz" else 1.0)):
                    raise Eingabefehler(f"{ort}: faktor {f!r} ungültig (zulässig 0 bis {fmax if art == 'Freisitz' else 1.0})")
                if d["regelwerk"] == "DIN_277" and f != 1.0:
                    raise Eingabefehler(f"{ort}: DIN 277 kennt keine Anrechnungsfaktoren (faktor muss 1 sein)")
                if f == 0:
                    warn.append(f"{ort}: faktor 0 (Fläche wird nicht angerechnet)")
        a = w.get("angabe_auftraggeber")
        if a is not None and (not zahl(a) or a <= 0):
            raise Eingabefehler(f"{w['name']}: angabe_auftraggeber muss eine Zahl > 0 sein oder fehlen")
    return warn


def putzabzug(d):
    """Fertigmaße: immer 0 %. Rohbaumaße: Standard 3 % (Büro-Standard), überschreibbar."""
    if not REGELWERKE[d["regelwerk"]]["abzug"] or d.get("massart", "roh") == "fertig":
        return 0.0
    return float(d.get("putzabzug", 0.03))


def fill(farbe):
    return PatternFill("solid", fgColor=farbe)


def zelle(ws, ref, wert=None, fett=False, fmt=None, farbe=None, ausr=None, kursiv=False, rahmen=True, text=False):
    c = ws[ref]
    if wert is not None:
        c.value = wert
        if text and isinstance(wert, str):
            c.data_type = "s"  # nie als Formel interpretieren (z. B. Name beginnt mit "=")
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
    name = "".join(ch for ch in name if ch.isprintable() and ch not in "[]:*?/\\")
    name = " ".join(name.split()).strip("'").strip()
    if not name:
        raise Eingabefehler("Blattname wäre leer")
    return name[:31].strip("'").strip()


def q(blatt):
    """Blattverweis mit korrekt verdoppelten Apostrophen."""
    return "'" + blatt.replace("'", "''") + "'!"


def parameter_blatt(wb, d):
    ws = wb.active
    ws.title = "Parameter"
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 70
    zeilen = [
        ("Projekt / Aktenzeichen", d.get("projekt", "")),
        ("Bauzustand (Plangrundlage)", d.get("bauzustand", "")),
        ("Regelwerk", d["regelwerk"]),
        ("Maßart", {"roh": "Rohbaumaße aus Bauzeichnung", "fertig": "Fertigmaße (lichte Maße)"}[d.get("massart", "roh")]),
        ("Putz- und Belagabzug", putzabzug(d)),
        ("Quelle der Maße", d.get("massquelle", "")),
        ("Datum", d.get("datum", "")),
    ]
    for i, (k, v) in enumerate(zeilen, start=1):
        zelle(ws, f"A{i}", k, fett=True, farbe=BLAU)
        zelle(ws, f"B{i}", v, fmt="0.0%" if k.startswith("Putz") else None, ausr="left", text=True)
    extra = []
    if putzabzug(d) not in (0.0, 0.03) and REGELWERKE[d["regelwerk"]]["abzug"]:
        extra.append(f"Der Putz- und Belagabzug weicht vom Büro-Standard (3,0 %) ab: {putzabzug(d):.1%}.")
    if d.get("pauschalabzug_44_abs3"):
        extra.append(f"Zusätzlicher Pauschalabzug nach § 44 Abs. 3 II. BV a. F.: {d['pauschalabzug_44_abs3']:.1%} (Sekundärquelle, Voraussetzungen im Einzelfall prüfen).")
    for i, h in enumerate(REGELWERKE[d["regelwerk"]]["hinweise"] + extra + [HINWEIS_PLAN], start=len(zeilen) + 2):
        ws.merge_cells(f"A{i}:B{i}")
        zelle(ws, f"A{i}", h, kursiv=True, ausr="left", rahmen=False, text=True)
        ws.row_dimensions[i].height = 30
    return "Parameter!$B$5"


def wohnung_blatt(wb, w, d, putz_ref):
    reg = REGELWERKE[d["regelwerk"]]
    ws = wb.create_sheet(blatt_name(w))
    for sp, br in zip("ABCDEFG", (34, 11, 11, 15, 10, 16, 56)):
        ws.column_dimensions[sp].width = br
    ws.merge_cells("A1:G1")
    zelle(ws, "A1", reg["titel"], fett=True, ausr="left")
    ws.merge_cells("A3:G3")
    zelle(ws, "A3", f"{w['name']} — Geschoss {w['geschoss']}", fett=True, farbe=BLAU, ausr="left", text=True)
    kopf = ["Raum / Teilfläche", "Länge [m]", "Breite [m]", "Grundfläche [m²]", "Faktor", "anrechenbar [m²]", "Anmerkung, lichte Höhe"]
    for sp, t in zip("ABCDEFG", kopf):
        zelle(ws, f"{sp}4", t, fett=True, farbe=BLAU, ausr="center")
    info = []

    def raumzeile(r, z, art):
        zelle(ws, f"A{z}", str(r["name"]), text=True)
        zelle(ws, f"B{z}", r["laenge"], fmt="0.00")
        zelle(ws, f"C{z}", r["breite"], fmt="0.00")
        zelle(ws, f"D{z}", f"=ROUND(B{z}*C{z},3)", fmt="0.00")
        zelle(ws, f"E{z}", 1.0 if r.get("faktor") is None else r["faktor"], fmt="0.00")
        zelle(ws, f"F{z}", f"=ROUND(D{z}*E{z},3)", fmt="0.00")
        zelle(ws, f"G{z}", str(r.get("anmerkung", "")), ausr="left", text=True)
        info.append((z, art))

    zeile = 5
    erste = zeile
    for r in w["raeume"]:
        raumzeile(r, zeile, 'Raum')
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
    zelle(ws, f"F{abz}", f"=-ROUND(F{zs}*E{abz},3)", fmt="0.00", fett=True)
    zelle(ws, f"G{abz}", "Büro-Standard, siehe Blatt Parameter" if d["regelwerk"] == "WoFlV" else "siehe Blatt Parameter", kursiv=True, ausr="left")
    zelle(ws, f"A{nach}", "Grundfläche der Räume nach Abzug", fett=True)
    for sp in "BCDE":
        zelle(ws, f"{sp}{nach}")
    zelle(ws, f"F{nach}", f"=F{zs}+F{abz}", fett=True, fmt="0.00")
    zelle(ws, f"G{nach}")
    basis = nach
    pa = d.get("pauschalabzug_44_abs3") or 0
    if pa:
        pab, nach2 = nach + 1, nach + 2
        zelle(ws, f"A{pab}", "Pauschalabzug § 44 Abs. 3 II. BV a. F.", fett=True)
        for sp in "BCD":
            zelle(ws, f"{sp}{pab}", farbe=ORANGE)
        zelle(ws, f"E{pab}", pa, fmt="0.0%", farbe=ORANGE)
        zelle(ws, f"F{pab}", f"=-ROUND(F{nach}*E{pab},3)", fmt="0.00", fett=True)
        zelle(ws, f"G{pab}", "Sekundärquelle, Voraussetzungen im Einzelfall prüfen", kursiv=True, ausr="left")
        zelle(ws, f"A{nach2}", "Grundfläche der Räume nach Abzügen", fett=True)
        for sp in "BCDE":
            zelle(ws, f"{sp}{nach2}")
        zelle(ws, f"F{nach2}", f"=F{nach}+F{pab}", fett=True, fmt="0.00")
        zelle(ws, f"G{nach2}")
        basis = nach2
    zeile = basis + 1
    ws.merge_cells(f"A{zeile}:G{zeile}")
    zelle(ws, f"A{zeile}", reg["freisitz"], fett=True, farbe=ORANGE, ausr="left")
    zeile += 1
    f_erste = zeile
    freisitze = w.get("freisitze") or []
    for r in freisitze:
        raumzeile(r, zeile, 'Freisitz')
        zeile += 1
    if not freisitze:  # leere Zeile zeigt das Layout, bleibt aber ohne Wert und ohne Raumliste-Eintrag
        for sp in "ABCDEFG":
            zelle(ws, f"{sp}{zeile}")
        zelle(ws, f"F{zeile}", 0, fmt="0.00")
        zeile += 1
    fs = zeile
    zelle(ws, f"A{fs}", "Zwischensumme Freisitze (angerechnet)", fett=True)
    for sp in "BCDE":
        zelle(ws, f"{sp}{fs}")
    zelle(ws, f"F{fs}", f"=SUM(F{f_erste}:F{fs - 1})", fett=True, fmt="0.00")
    zelle(ws, f"G{fs}")
    wf = fs + 1
    zelle(ws, f"A{wf}", reg["ende"].format(w=w["name"]), fett=True, farbe=GRUEN, text=True)
    for sp in "BCDE":
        zelle(ws, f"{sp}{wf}", farbe=GRUEN)
    zelle(ws, f"F{wf}", f"=F{basis}+F{fs}", fett=True, fmt="0.00", farbe=GRUEN)
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
    zelle(ws, f"E{abw}", f'=IF(N(F{ang})=0,"",F{wf}/F{ang}-1)', fmt="+0.0%;-0.0%")
    zelle(ws, f"F{abw}", f'=IF(N(F{ang})=0,"",F{wf}-F{ang})', fmt="+0.00;-0.00")
    zelle(ws, f"G{abw}", "Spalte E zeigt die Abweichung als Anteil der Angabe", kursiv=True, ausr="left")
    ws.freeze_panes = "A5"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    return ws.title, info, wf


def werte_einbetten(pfad):
    """Rechnet die Formeln mit LibreOffice neu und ersetzt die Datei durch die Fassung mit gespeicherten Werten."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise Eingabefehler("--mit-werten benötigt LibreOffice (soffice). Alternativ Datei in Excel öffnen und speichern.")
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run([soffice, "--headless", "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", tmp, pfad],
                           capture_output=True, text=True)
        neu = os.path.join(tmp, os.path.basename(pfad))
        if r.returncode != 0 or not os.path.exists(neu):
            raise Eingabefehler("Neuberechnung mit LibreOffice fehlgeschlagen: " + r.stderr.strip()[:200])
        shutil.copyfile(neu, pfad)


def main(eingabe, ausgabe, ueberschreiben=False, mit_werten=False):
    try:
        d = json.load(open(eingabe, encoding="utf-8"))
    except FileNotFoundError:
        raise Eingabefehler(f"Eingabedatei nicht gefunden: {eingabe}")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise Eingabefehler(f"Eingabedatei ist kein gültiges JSON (UTF-8): {e}")
    for hinweis in pruefe(d):
        print("HINWEIS:", hinweis, file=sys.stderr)
    if os.path.exists(ausgabe) and not ueberschreiben:
        raise Eingabefehler(f"Zieldatei existiert bereits: {ausgabe}. Mit --ueberschreiben ersetzen (Freigabe einholen).")
    wb = Workbook()
    putz_ref = parameter_blatt(wb, d)
    ws2 = wb.create_sheet("Übersicht")
    for sp, t in zip("ABC", ("Wohnung", "Geschoss", "Wohnfläche [m²]")):
        zelle(ws2, f"{sp}1", t, fett=True, farbe=BLAU, ausr="center")
    for sp, br in zip("ABC", (22, 12, 18)):
        ws2.column_dimensions[sp].width = br
    daten = []
    namen = set()
    for i, w in enumerate(d["wohnungen"], start=2):
        blatt = blatt_name(w)
        if blatt.lower() in namen:
            raise Eingabefehler(f"Blattname nach Kürzung nicht eindeutig: {blatt!r}. Namen kürzer oder verschieden wählen.")
        namen.add(blatt.lower())
        name, info, wf = wohnung_blatt(wb, w, d, putz_ref)
        daten.append((name, info, w))
        zelle(ws2, f"A{i}", str(w["name"]), text=True)
        zelle(ws2, f"B{i}", str(w["geschoss"]), text=True)
        zelle(ws2, f"C{i}", f"={q(name)}F{wf}", fmt="0.00", fett=True)
    ende = len(d["wohnungen"]) + 2
    zelle(ws2, f"A{ende}", "Summe", fett=True)
    zelle(ws2, f"B{ende}")
    zelle(ws2, f"C{ende}", f"=SUM(C2:C{ende - 1})", fmt="0.00", fett=True)
    ws = wb.create_sheet("Raumliste")
    kopf = ["Wohnung", "Geschoss", "Art", "Raum / Teilfläche", "Länge [m]", "Breite [m]", "Grundfläche [m²]", "Faktor", "anrechenbar [m²]"]
    for i, t in enumerate(kopf, start=1):
        zelle(ws, f"{get_column_letter(i)}1", t, fett=True, farbe=BLAU, ausr="center")
        ws.column_dimensions[get_column_letter(i)].width = [14, 10, 10, 34, 11, 11, 16, 9, 16][i - 1]
    z = 2
    for blatt, info, w in daten:
        for zz, art in info:
            zelle(ws, f"A{z}", str(w["name"]), text=True)
            zelle(ws, f"B{z}", str(w["geschoss"]), text=True)
            zelle(ws, f"C{z}", art)
            zelle(ws, f"D{z}", f"={q(blatt)}A{zz}")
            for sp, qs in zip("EFGHI", "BCDEF"):
                zelle(ws, f"{sp}{z}", f"={q(blatt)}{qs}{zz}", fmt="0.00")
            z += 1
    ws.freeze_panes = "A2"
    wb.save(ausgabe)
    if mit_werten:
        werte_einbetten(ausgabe)
    print(f"geschrieben: {ausgabe}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) != 2 or not flags <= {"--ueberschreiben", "--mit-werten"}:
        sys.exit(__doc__)
    try:
        main(args[0], args[1], "--ueberschreiben" in flags, "--mit-werten" in flags)
    except Eingabefehler as e:
        sys.exit(f"FEHLER: {e}")
    except (KeyError, TypeError, ValueError, AttributeError) as e:
        sys.exit(f"FEHLER: Eingabe hat ein unerwartetes Format ({type(e).__name__}: {e}). Siehe references/eingabeformat.md")
