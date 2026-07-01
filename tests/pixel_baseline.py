#!/usr/bin/env python3
"""Harnais de non-regression pixel pour Beautiful Tides.

Genere des images de reference avec le pipeline de rendu et compare
l'avant/apres refactorisation. Objectif : la sortie doit rester
IDENTIQUE AU PIXEL pour les fonds deterministes.

Usage :
    python tests/pixel_baseline.py --capture   # avant refacto -> tests/baseline/
    python tests/pixel_baseline.py --check     # apres refacto -> compare

Le fond 2 (cercles aleatoires non seedes) est intrinsequement non
reproductible : il est verifie structurellement (dimensions) seulement.
"""
import argparse
import os
import shutil
import sys

import numpy as np
import cv2

# Se placer a la racine du projet quel que soit le cwd d'appel
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import fonctions  # noqa: E402

BASELINE_DIR = os.path.join("tests", "baseline")
OUTPUT_DIR = "OUTPUT IMAGES"

# Configuration du scenario de reference (donnees presentes en base)
PORT = "boucau-46"
YEAR = "2026"
SIZE = 100
MONTHS = ["janvier"]          # un mois suffit a exercer tout le pipeline
STRICT_FONDS = "1345678"      # fonds deterministes (verif diff==0)
STRUCT_FONDS = "2"            # fond aleatoire (verif dimensions seulement)


def _generate(fonds):
    """Genere OUTPUT IMAGES/base_<f>.png pour chaque fond de la chaine."""
    fonctions.creation_image_complete(YEAR, MONTHS, PORT, SIZE, fonds, "base.png")
    return {f: os.path.join(OUTPUT_DIR, f"base_{f}.png") for f in fonds}


def capture():
    os.makedirs(BASELINE_DIR, exist_ok=True)
    produced = _generate(STRICT_FONDS + STRUCT_FONDS)
    for f, path in produced.items():
        dst = os.path.join(BASELINE_DIR, f"base_{f}.png")
        shutil.copyfile(path, dst)
        img = cv2.imread(dst)
        print(f"[CAPTURE] fond {f}: {img.shape} -> {dst}")
    print(f"\n{len(produced)} references ecrites dans {BASELINE_DIR}/")


def check():
    if not os.path.isdir(BASELINE_DIR):
        print("[ERREUR] Pas de baseline. Lancez d'abord --capture.")
        return 1
    produced = _generate(STRICT_FONDS + STRUCT_FONDS)
    failures = 0
    for f, path in produced.items():
        ref = os.path.join(BASELINE_DIR, f"base_{f}.png")
        if not os.path.exists(ref):
            print(f"[SKIP] fond {f}: pas de reference")
            continue
        a = cv2.imread(ref)
        b = cv2.imread(path)
        if a.shape != b.shape:
            print(f"[FAIL] fond {f}: dimensions {a.shape} != {b.shape}")
            failures += 1
            continue
        if f in STRUCT_FONDS:
            print(f"[OK-struct] fond {f}: dimensions identiques {a.shape} (fond aleatoire, diff non exigee)")
            continue
        diff = cv2.absdiff(a, b)
        maxd = int(diff.max())
        nnz = int(np.count_nonzero(diff))
        if maxd == 0:
            print(f"[OK] fond {f}: diff pixel = 0")
        else:
            print(f"[FAIL] fond {f}: max diff={maxd}, pixels differents={nnz}")
            cv2.imwrite(os.path.join(BASELINE_DIR, f"DIFF_{f}.png"), diff * 20)
            failures += 1
    if failures:
        print(f"\n{failures} fond(s) en echec — la sortie a change !")
        return 1
    print("\nTous les fonds deterministes sont identiques au pixel pres. OK.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.capture:
        capture()
    elif args.check:
        sys.exit(check())
    else:
        ap.print_help()
