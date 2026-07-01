"""Acces centralise a la liste des ports (source : data/ports.json).

Remplace l'ancienne liste codee en dur `AVAILABLE_PORTS` de interface.py et
supprime l'import circulaire scrap_all -> interface. Fournit aussi l'ajout de
nouveaux ports depuis l'interface.
"""
import json
import os
import re

from unidecode import unidecode

_HERE = os.path.dirname(os.path.abspath(__file__))
PORTS_JSON = os.path.join(_HERE, "data", "ports.json")


def load_ports():
    """Retourne la liste des ports : [{name, code, lat, lon, region, coast}, ...]."""
    with open(PORTS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("ports", []))


def available_ports():
    """Compatibilite : liste de tuples (name, code) comme l'ancien AVAILABLE_PORTS."""
    return [(p["name"], p["code"]) for p in load_ports()]


def get_port_by_code(code):
    code = str(code)
    for p in load_ports():
        if str(p["code"]) == code:
            return p
    return None


def coasts():
    """Liste ordonnee des cotes presentes (pour grouper dans l'UI)."""
    order = ["Mer du Nord", "Manche", "Atlantique", "Mediterranee", "Corse"]
    present = {p.get("coast", "Autre") for p in load_ports()}
    ordered = [c for c in order if c in present]
    ordered += sorted(present - set(order))
    return ordered


def add_port(name, code, lat=None, lon=None, region="", coast="Atlantique"):
    """Ajoute (ou met a jour) un port dans data/ports.json.

    Retourne (ok, message).
    """
    name = (name or "").strip()
    code = str(code or "").strip()
    if not name or not code:
        return False, "Nom et code sont obligatoires."
    if not code.isdigit():
        return False, "Le code meteoconsult doit etre un nombre."

    with open(PORTS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    ports = data.setdefault("ports", [])

    for p in ports:
        if str(p["code"]) == code:
            return False, f"Le code {code} existe deja ({p['name']})."

    entry = {"name": name, "code": code, "region": region, "coast": coast}
    try:
        entry["lat"] = float(lat) if lat is not None and str(lat) != "" else None
        entry["lon"] = float(lon) if lon is not None and str(lon) != "" else None
    except ValueError:
        entry["lat"], entry["lon"] = None, None
    ports.append(entry)

    with open(PORTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True, f"Port '{name}' ({code}) ajoute."


def port_slug(name, code):
    """Formatte le slug meteoconsult : 'les-sables-d-olonne-1025'.

    Normalise correctement les accents et apostrophes (unidecode + tout
    caractere non alphanumerique -> tiret), sinon les ports comportant une
    apostrophe ou un accent construisent une URL invalide (404).
    """
    base = re.sub(r"[^a-z0-9]+", "-", unidecode(name).lower()).strip("-")
    return f"{base}-{code}"
