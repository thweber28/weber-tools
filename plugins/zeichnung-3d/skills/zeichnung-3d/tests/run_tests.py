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


def lauf(daten, name):
    ein, aus = os.path.join(tmp, f"{name}.json"), os.path.join(tmp, f"{name}.xlsx")
    json.dump(daten, open(ein, "w", encoding="utf-8"))
    return subprocess.run([sys.executable, SKRIPT, ein, aus], capture_output=True, text=True), aus


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
check("Raumliste ohne leere Zeile", all(r[2] not in (None, 0, "0") for r in wb["Raumliste"].iter_rows(min_row=2, values_only=True)))
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

shutil.rmtree(tmp, ignore_errors=True)
print("\nFEHLER:", fehler if fehler else "keine")
sys.exit(1 if fehler else 0)
