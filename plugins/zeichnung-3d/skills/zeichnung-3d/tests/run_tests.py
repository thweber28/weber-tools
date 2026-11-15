#!/usr/bin/env python3
"""Tests für wohnflaeche_xlsx.py. Rechnet die Excel-Formeln mit LibreOffice nach (soffice nötig)."""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

import openpyxl

HIER = os.path.dirname(os.path.abspath(__file__))
SKRIPT = os.path.join(HIER, "..", "scripts", "wohnflaeche_xlsx.py")
BEISPIEL = json.load(open(os.path.join(HIER, "..", "examples", "beispiel_eingabe.json"), encoding="utf-8"))
tmp = tempfile.mkdtemp()
fehler = []


def lauf(daten, name, *extra, roh=None):
    ein, aus = os.path.join(tmp, f"{name}.json"), os.path.join(tmp, f"{name}.xlsx")
    if roh is not None:
        open(ein, "w", encoding="utf-8").write(roh)
    else:
        json.dump(daten, open(ein, "w", encoding="utf-8"))
    return subprocess.run([sys.executable, SKRIPT, ein, aus, *extra], capture_output=True, text=True), aus


def werte(xlsx):
    out = os.path.join(tmp, "calc")
    subprocess.run(["soffice", "--headless", "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", out, xlsx], capture_output=True)
    return openpyxl.load_workbook(os.path.join(out, os.path.basename(xlsx)), data_only=True)


def check(name, bedingung, info=""):
    print(("OK   " if bedingung else "FAIL ") + name + (f" ({info})" if info and not bedingung else ""))
    if not bedingung:
        fehler.append(name)


def wf(wb, blatt):
    ws = wb[blatt]
    for r in ws.iter_rows(values_only=True):
        if r[0] and str(r[0]).startswith(("Wohnfläche ", "Netto-Raumfläche ")):
            return r[5]


# 1 Beispiel (Handrechnung: 72,299 und 50,595)
p, x = lauf(BEISPIEL, "basis")
wb = werte(x)
check("Beispiel läuft", p.returncode == 0, p.stderr)
check("Wohnung 1 = 72,299", abs(wf(wb, "Wohnung 1 - EG") - 72.299) < 0.001)
check("Wohnung 2 = 50,595", abs(wf(wb, "Wohnung 2 - OG") - 50.595) < 0.001)
check("Übersicht-Summe", abs(wb["Übersicht"]["C4"].value - 122.894) < 0.001)

# 2 Fertigmaße: Abzug immer 0, auch bei gesetztem putzabzug
d = copy.deepcopy(BEISPIEL); d["massart"] = "fertig"; d["putzabzug"] = 0.03
p, x = lauf(d, "fertig")
check("fertig: Abzug 0 %", abs(wf(werte(x), "Wohnung 1 - EG") - 74.419) < 0.001, p.stderr)

# 3 Apostroph im Namen: keine Fehlerwerte
d = copy.deepcopy(BEISPIEL); d["wohnungen"][0]["name"] = "Whg 'A'"
p, x = lauf(d, "apos")
wb = werte(x)
check("Apostroph: Übersicht ohne Fehler", isinstance(wb["Übersicht"]["C2"].value, (int, float)), wb["Übersicht"]["C2"].value)

# 4 Pflichtfelder / Validierung
d = copy.deepcopy(BEISPIEL); del d["wohnungen"][0]["raeume"][0]["breite"]
check("fehlende Breite bricht ab", lauf(d, "nb")[0].returncode != 0)
d = copy.deepcopy(BEISPIEL); del d["wohnungen"][0]["freisitze"][0]["faktor"]
check("Freisitz ohne Faktor bricht ab", lauf(d, "nf")[0].returncode != 0)
d = copy.deepcopy(BEISPIEL); d["wohnungen"][0]["freisitze"][0]["faktor"] = 0.8
check("Freisitzfaktor > 0,5 bricht ab", lauf(d, "f8")[0].returncode != 0)
d = copy.deepcopy(BEISPIEL); d["regelwerk"] = "XYZ"
check("ungültiges Regelwerk bricht ab", lauf(d, "rw")[0].returncode != 0)
d = copy.deepcopy(BEISPIEL); d["wohnungen"].append(copy.deepcopy(d["wohnungen"][0]))
check("doppelte Wohnung/Geschoss bricht ab", lauf(d, "dup")[0].returncode != 0)

# 5 ohne Freisitze, ohne Angabe, Angabe 0
d = copy.deepcopy(BEISPIEL); d["wohnungen"][1]["freisitze"] = []; d["wohnungen"][1].pop("angabe_auftraggeber", None)
p, x = lauf(d, "ohnefs")
wb = werte(x)
check("ohne Freisitze: 49,47", abs(wf(wb, "Wohnung 2 - OG") - 49.47) < 0.001, p.stderr)
check("Raumliste ohne leere Zeile", all(r[3] not in (None, 0, "0") for r in wb["Raumliste"].iter_rows(min_row=2, values_only=True)))
d = copy.deepcopy(BEISPIEL); d["wohnungen"][0]["angabe_auftraggeber"] = 0
check("Angabe 0 bricht ab", lauf(d, "a0")[0].returncode != 0)

# 6 DIN 277: kein Abzug, Faktor nur 1, Beschriftung Netto-Raumfläche
d = copy.deepcopy(BEISPIEL); d["regelwerk"] = "DIN_277"
check("DIN 277 mit Faktor 0,5 bricht ab", lauf(d, "din_f")[0].returncode != 0)
for w in d["wohnungen"]:
    for r in w["raeume"] + w["freisitze"]:
        r["faktor"] = 1.0
p, x = lauf(d, "din")
wb = werte(x)
check("DIN 277: Titel und kein Abzug", p.returncode == 0 and wb["Parameter"]["B5"].value == 0 and "Netto-Raumfläche" in str([c.value for c in wb["Wohnung 1 - EG"]["A"]]))

# 7 II. BV a. F.
d = copy.deepcopy(BEISPIEL); d["regelwerk"] = "II_BV_aF"
p, x = lauf(d, "iibv")
check("II. BV a. F. läuft, Titel", p.returncode == 0 and "II. BV" in str(werte(x)["Wohnung 1 - EG"]["A1"].value), p.stderr)

# 8 Formel-Injektion über Raumnamen
d = copy.deepcopy(BEISPIEL); d["wohnungen"][0]["raeume"][0]["name"] = "=1+1"
p, x = lauf(d, "inj")
check("Raumname '=1+1' bleibt Text", werte(x)["Wohnung 1 - EG"]["A5"].value == "=1+1")

# 9 Prüfer-Befunde Lauf 2: keine stillen Nullen, Klartext statt Traceback
def fehlerfrei_abbruch(name, daten=None, roh=None, erwartet="FEHLER"):
    p, _ = lauf(daten, name, roh=roh)
    check(name, p.returncode != 0 and erwartet in p.stderr and "Traceback" not in p.stderr, p.stderr[-200:])


d = copy.deepcopy(BEISPIEL); d["wohnungen"][0]["raeume"][0]["faktor"] = None
fehlerfrei_abbruch("faktor null bricht ab", d)
for wert, nm in ((float("nan"), "nan"), (float("inf"), "inf"), (1e308, "riesig"), (-1.0, "negativ")):
    d = copy.deepcopy(BEISPIEL); d["wohnungen"][0]["raeume"][0]["laenge"] = wert
    fehlerfrei_abbruch(f"Länge {nm} bricht ab", d)
for wert in (-0.5, 1.5, "3%", None, True):
    d = copy.deepcopy(BEISPIEL); d["putzabzug"] = wert
    fehlerfrei_abbruch(f"putzabzug {wert!r} bricht ab", d)
d = copy.deepcopy(BEISPIEL); d["wohnungen"][0]["angabe_auftraggeber"] = True
fehlerfrei_abbruch("angabe true bricht ab", d)
fehlerfrei_abbruch("JSON ungültig", roh="{kaputt")
fehlerfrei_abbruch("Wurzel Liste", roh="[1,2]")
fehlerfrei_abbruch("Wohnung als String", roh=json.dumps({"regelwerk": "WoFlV", "wohnungen": ["x"]}))
fehlerfrei_abbruch("Raum als String", roh=json.dumps({"regelwerk": "WoFlV", "wohnungen": [{"name": "a", "geschoss": "EG", "raeume": ["x"]}]}))
p = subprocess.run([sys.executable, SKRIPT, os.path.join(tmp, "gibtsnicht.json"), os.path.join(tmp, "x.xlsx")], capture_output=True, text=True)
check("Datei fehlt: Klartext", p.returncode != 0 and "FEHLER" in p.stderr and "Traceback" not in p.stderr)

# Blattnamen
for nm in ("'Whg", "'", "Whg\nA", "Whg 'A'", "A" * 60):
    d = copy.deepcopy(BEISPIEL); d["wohnungen"][0]["name"] = nm
    p, x = lauf(d, "bn")
    if p.returncode == 0:
        wb = werte(x)
        check(f"Blattname {nm!r}: Übersicht ohne Fehler", isinstance(wb["Übersicht"]["C2"].value, (int, float)), wb["Übersicht"]["C2"].value)
        os.remove(x)
    else:
        check(f"Blattname {nm!r}: sauberer Abbruch", "FEHLER" in p.stderr and "Traceback" not in p.stderr, p.stderr[-150:])

# Überschreibschutz
p, x = lauf(BEISPIEL, "ow")
p2, _ = lauf(BEISPIEL, "ow")
check("Überschreiben ohne Flag verweigert", p2.returncode != 0 and "ueberschreiben" in p2.stderr)
p3, _ = lauf(BEISPIEL, "ow", "--ueberschreiben")
check("Überschreiben mit Flag", p3.returncode == 0)

# Werte einbetten (gecachte Werte lesbar ohne Neuberechnung)
p, x = lauf(BEISPIEL, "cache", "--mit-werten")
wbv = openpyxl.load_workbook(x, data_only=True)
check("--mit-werten: gecachte Werte", p.returncode == 0 and abs(wbv["Übersicht"]["C2"].value - 72.299) < 0.001, p.stderr)
wbf = openpyxl.load_workbook(x)
check("--mit-werten: Formeln bleiben erhalten", str(wbf["Wohnung 1 - EG"]["D5"].value).startswith("="))

# Raumliste Art, II. BV Pauschalabzug § 44 Abs. 3
p, x = lauf(BEISPIEL, "art")
arten = {r[2] for r in werte(x)["Raumliste"].iter_rows(min_row=2, values_only=True)}
check("Raumliste kennzeichnet Raum/Freisitz", arten == {"Raum", "Freisitz"}, arten)
d = copy.deepcopy(BEISPIEL); d["regelwerk"] = "II_BV_aF"; d["pauschalabzug_44_abs3"] = 0.1
p, x = lauf(d, "pa")
# Wohnung 2: 51 * 0,97 = 49,47; -10 % = 44,523; + Balkon 1,125 = 45,648
check("§ 44 Abs. 3: 10 % Pauschalabzug", p.returncode == 0 and abs(wf(werte(x), "Wohnung 2 - OG") - 45.648) < 0.001, p.stderr)
d = copy.deepcopy(BEISPIEL); d["pauschalabzug_44_abs3"] = 0.1
check("§ 44 Abs. 3 nur bei II. BV a. F.", lauf(d, "pa2")[0].returncode != 0)

# Kopie des Blender-Prompts nicht auseinanderlaufen lassen
orig = os.path.join(HIER, "..", "..", "..", "..", "..", "Vorlagen", "Textbausteine", "Prompts", "blender-3d-walkthrough.md")
kopie = os.path.join(HIER, "..", "references", "blender-workflow.md")
if os.path.exists(orig):
    check("blender-workflow.md identisch zur Vorlage", open(orig, encoding="utf-8").read() == open(kopie, encoding="utf-8").read())

shutil.rmtree(tmp, ignore_errors=True)
print("\nFEHLER:", fehler if fehler else "keine")
sys.exit(1 if fehler else 0)
