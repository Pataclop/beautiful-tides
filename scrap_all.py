#!/usr/bin/env python3
"""
Script pour scraper automatiquement tous les ports et stocker les données
dans la base de données pour une année donnée.
"""

import sys
import os
from datetime import datetime

# Ajouter le répertoire courant au path pour importer les modules locaux
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import fonctions
from interface import AVAILABLE_PORTS

# Configuration
ANNEE_CIBLE = "2026"  # Année à scraper
MOIS = [
    'janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin',
    'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre'
]

URL_BASE = 'https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees'

def scrap_tous_les_ports():
    """
    Scraper tous les ports pour l'année cible
    """
    print("🚀 Démarrage du scraping automatique de tous les ports")
    print(f"📅 Année cible: {ANNEE_CIBLE}")
    print(f"🏖️ Nombre de ports à traiter: {len(AVAILABLE_PORTS)}")
    print(f"📊 Nombre total d'opérations: {len(AVAILABLE_PORTS) * len(MOIS)}")
    print("=" * 60)

    # Initialiser la base de données
    print("🗄️ Initialisation de la base de données...")
    fonctions.init_database()
    print("✅ Base de données initialisée")
    print()

    total_operations = len(AVAILABLE_PORTS) * len(MOIS)
    operation_count = 0
    success_count = 0
    error_count = 0

    start_time = datetime.now()

    # Traiter chaque port
    for port_idx, (port_name, port_code) in enumerate(AVAILABLE_PORTS, 1):
        print(f"🏖️ Port {port_idx}/{len(AVAILABLE_PORTS)}: {port_name} ({port_code})")
        print("-" * 50)

        port_success_count = 0

        # S'assurer que le port existe dans la base
        if not fonctions.ensure_port_in_db(port_name, port_code):
            print(f"  ⚠️ Impossible de créer le port {port_name} dans la base")
            error_count += len(MOIS)  # Compter comme échec pour tous les mois
            continue

        # Traiter chaque mois pour ce port
        for month in MOIS:
            operation_count += 1

            # Formatter le nom du port (minuscules, tirets)
            port_formatted = f"{port_name.lower().replace(' ', '-')}-{port_code}"

            print(f"  📥 [{operation_count}/{total_operations}] {month} {ANNEE_CIBLE} - {port_formatted}...")

            try:
                # Appeler la fonction de récupération
                result = fonctions.recuperation_et_sauvegarde_url(
                    URL_BASE,
                    port_formatted,
                    month,
                    ANNEE_CIBLE
                )

                if result and len(result.strip()) > 0:
                    print("  ✅ OK")
                    port_success_count += 1
                    success_count += 1
                else:
                    print("  ❌ Échec (pas de données)")
                    error_count += 1

            except Exception as e:
                print(f"  ❌ Erreur: {e}")
                error_count += 1

        # Résumé pour ce port
        port_total = len(MOIS)
        print(f"📊 Port {port_name}: {port_success_count}/{port_total} mois réussis")
        print()

    # Résumé final
    end_time = datetime.now()
    duration = end_time - start_time

    print("=" * 60)
    print("🎉 SCRAPING TERMINÉ")
    print("=" * 60)
    print(f"⏱️ Durée totale: {duration}")
    print(f"📊 Statistiques:")
    print(f"  • Opérations totales: {total_operations}")
    print(f"  • Réussites: {success_count}")
    print(f"  • Échecs: {error_count}")
    print(f"  • Taux de succès: {(success_count/total_operations*100):.1f}%")
    print(f"🏖️ Ports traités: {len(AVAILABLE_PORTS)}")

    if success_count > 0:
        print("✅ Scraping terminé avec succès !")
    else:
        print("❌ Aucune donnée n'a pu être récupérée.")
        return False

    return True

def main():
    """
    Fonction principale
    """
    try:
        success = scrap_tous_les_ports()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Scraping interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erreur critique: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Permettre de changer l'année via argument en ligne de commande
    if len(sys.argv) > 1:
        ANNEE_CIBLE = sys.argv[1]
        print(f"📅 Année changée via argument: {ANNEE_CIBLE}")

    main()
