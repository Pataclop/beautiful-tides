#!/usr/bin/env python3
"""Remplissage de la base de donnees (sans generation d'images).

Recupere les donnees de marees d'une annee pour tous les ports (ou une
selection) et les stocke en base. Utilisable :
  - en ligne de commande :  python scrap_all.py [ANNEE]
  - depuis l'interface via la fonction reutilisable `fill_database(...)`.

Ce module n'importe QUE la couche de donnees (db) et la liste des ports
(ports) : il ne charge pas matplotlib/cv2, pour un demarrage leger.
"""
import sys
import os
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import db
import ports as ports_module

URL_BASE = "https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees"
MOIS = [
    "janvier", "fevrier", "mars", "avril", "mai", "juin",
    "juillet", "aout", "septembre", "octobre", "novembre", "decembre",
]


def fill_database(year, ports=None, months=None, progress_cb=None,
                  cancel=None, skip_complete=True, future_only=True, delay=3.0):
    """Remplit la base pour l'annee donnee, sans generer d'images.

    Note : meteoconsult ne publie que les mois a venir (les mois passes et, en
    general, l'annee suivante renvoient une 404). Les mois indisponibles sont
    ignores proprement. Le site limite aussi la frequence des requetes : un
    delai est applique entre deux telechargements reels.

    Args:
        year (str|int): annee cible, ex "2026".
        ports: liste de dicts {name, code} ou de tuples (name, code).
               Par defaut : tous les ports de data/ports.json.
        months: liste de mois (noms francais). Par defaut : les 12 mois.
        progress_cb: callback optionnel progress_cb(done, total, message).
        cancel: callable renvoyant True pour interrompre, ou objet .is_set().
        skip_complete: ne pas re-recuperer un mois deja complet en base.
        future_only: n'interroger que les mois non passes de l'annee (le
                     scrapper ne cherche pas les mois deja ecoules).
        delay: pause (secondes) entre deux telechargements reels, pour
               respecter la limite de frequence du site.

    Returns:
        dict: statistiques {total, success, skipped, errors, duration_s}.
    """
    year = str(year)
    if ports is None:
        ports = ports_module.load_ports()
    if months is None:
        months = list(MOIS)
    if future_only:
        # Ne conserver que les mois futurs / en cours (voir db.future_months).
        months = db.future_months(year, months)

    # Normaliser en (name, code)
    norm = []
    for p in ports:
        if isinstance(p, dict):
            norm.append((p["name"], str(p["code"])))
        else:
            norm.append((p[0], str(p[1])))

    def cancelled():
        if cancel is None:
            return False
        if hasattr(cancel, "is_set"):
            return cancel.is_set()
        return bool(cancel())

    db.init_database()

    total = len(norm) * len(months)
    done = success = skipped = errors = 0
    start = datetime.now()

    for port_name, port_code in norm:
        if cancelled():
            break
        db.ensure_port_in_db(port_name, port_code)
        port_slug = ports_module.port_slug(port_name, port_code)

        for month in months:
            if cancelled():
                break
            done += 1
            month_num = db.MONTH_MAPPING.get(month, month)

            if skip_complete:
                _, is_complete, _, _ = db.check_complete_month_data(port_code, month_num, year)
                if is_complete:
                    skipped += 1
                    if progress_cb:
                        progress_cb(done, total, f"{port_name} {month}: deja complet")
                    continue

            if progress_cb:
                progress_cb(done, total, f"{port_name} {month}: recuperation...")
            try:
                result = db.recuperation_et_sauvegarde_url(URL_BASE, port_slug, month, year)
                if result and result.strip():
                    success += 1
                    msg = f"{port_name} {month}: OK"
                else:
                    errors += 1
                    msg = f"{port_name} {month}: echec"
            except Exception as e:
                errors += 1
                msg = f"{port_name} {month}: erreur {e}"
            if progress_cb:
                progress_cb(done, total, msg)

            # Throttle : respecter la limite de frequence du site (sauf en fin
            # de parcours ou si annulation demandee).
            if delay > 0 and not cancelled() and done < total:
                time.sleep(delay)

    duration = (datetime.now() - start).total_seconds()
    return {"total": total, "success": success, "skipped": skipped,
            "errors": errors, "duration_s": duration}


def pump_future(ports=None, progress_cb=None, cancel=None, delay=3.0,
                max_horizon=36, stop_after_failures=2, reference=None):
    """Aspire TOUT ce que le site publie : pour chaque port, avance mois par
    mois vers le futur (a partir du mois courant, sur plusieurs annees) et
    telecharge jusqu'a atteindre l'horizon (echecs consecutifs = plus de
    donnees disponibles).

    Args:
        ports: liste de dicts/tuples de ports (defaut : tous).
        progress_cb: callback progress_cb(done, total, message).
        cancel: callable/objet .is_set() pour interrompre.
        delay: pause (s) entre deux telechargements reels (limite de frequence).
        max_horizon: nombre max de mois explores par port (garde-fou).
        stop_after_failures: nombre d'echecs consecutifs avant de conclure que
            l'horizon est atteint pour ce port.
        reference: date de depart (defaut : maintenant).

    Returns:
        dict: statistiques {success, skipped, errors, ports, duration_s}.
    """
    if ports is None:
        ports = ports_module.load_ports()
    norm = []
    for p in ports:
        if isinstance(p, dict):
            norm.append((p["name"], str(p["code"])))
        else:
            norm.append((p[0], str(p[1])))

    def cancelled():
        if cancel is None:
            return False
        if hasattr(cancel, "is_set"):
            return cancel.is_set()
        return bool(cancel())

    db.init_database()
    calendar = db.upcoming_months(reference, max_horizon)
    total = len(norm)
    success = skipped = errors = 0
    start = datetime.now()

    for pidx, (port_name, port_code) in enumerate(norm, 1):
        if cancelled():
            break
        db.ensure_port_in_db(port_name, port_code)
        slug = ports_module.port_slug(port_name, port_code)
        consecutive_fail = 0

        for year, month in calendar:
            if cancelled():
                break
            month_num = db.MONTH_MAPPING.get(month, month)
            _, is_complete, _, _ = db.check_complete_month_data(port_code, month_num, year)
            if is_complete:
                skipped += 1
                consecutive_fail = 0
                if progress_cb:
                    progress_cb(pidx, total, f"{port_name} {month} {year}: deja complet")
                continue

            if progress_cb:
                progress_cb(pidx, total, f"{port_name} {month} {year}: recuperation...")
            try:
                result = db.recuperation_et_sauvegarde_url(URL_BASE, slug, month, year)
            except Exception as e:
                result = None
                if progress_cb:
                    progress_cb(pidx, total, f"{port_name} {month} {year}: erreur {e}")

            if result and result.strip():
                success += 1
                consecutive_fail = 0
                if progress_cb:
                    progress_cb(pidx, total, f"{port_name} {month} {year}: OK")
            else:
                consecutive_fail += 1
                errors += 1
                if progress_cb:
                    progress_cb(pidx, total, f"{port_name} {month} {year}: indisponible")
                if consecutive_fail >= stop_after_failures:
                    if progress_cb:
                        progress_cb(pidx, total, f"{port_name}: horizon atteint, port suivant.")
                    break

            if delay > 0 and not cancelled():
                time.sleep(delay)

    duration = (datetime.now() - start).total_seconds()
    return {"success": success, "skipped": skipped, "errors": errors,
            "ports": total, "duration_s": duration}


def main():
    def _cb(done, total, message):
        print(f"[{done}/{total}] {message}")

    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        # Mode annee precise : python scrap_all.py 2026
        year = sys.argv[1]
        print(f"Remplissage de la base pour l'annee {year} (mois a venir)...")
        stats = fill_database(year, progress_cb=_cb)
        print("=" * 50)
        print(f"Termine en {stats['duration_s']:.0f}s : "
              f"{stats['success']} OK, {stats['skipped']} deja complets, "
              f"{stats['errors']} echecs sur {stats['total']} operations.")
        return 0 if stats["success"] or stats["skipped"] else 1

    # Mode aspiration : tout ce qui est disponible, jusqu'a l'horizon.
    print("Aspiration de toutes les donnees a venir (jusqu'a l'horizon du site)...")
    stats = pump_future(progress_cb=_cb)
    print("=" * 50)
    print(f"Termine en {stats['duration_s']:.0f}s : {stats['success']} mois recuperes, "
          f"{stats['skipped']} deja complets, {stats['errors']} indisponibles "
          f"sur {stats['ports']} ports.")
    return 0 if stats["success"] or stats["skipped"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrompu par l'utilisateur")
        sys.exit(1)
