import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
import cv2
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from unidecode import unidecode
import unicodedata
import re
import math
import random
from matplotlib.font_manager import FontProperties
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import shutil
import sqlite3
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
Image.MAX_IMAGE_PIXELS = None

# Import optionnel de Playwright
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[INFO] Playwright non disponible - récupération limitée")

# Import du scrapper qui fonctionne
try:
    from scrapper import scrape_tide_data
    SCRAPPER_AVAILABLE = True
except ImportError:
    SCRAPPER_AVAILABLE = False
    print("[INFO] Scrapper non disponible - récupération limitée")

font_path = 'fonts/FUTURANEXTDEMIBOLDITALIC.TTF'  # Assurez-vous que le chemin est correct
font_path2 = 'fonts/SAIL.ttf'
font_path3 = 'fonts/SAIL_BOLD.ttf'
header_font = "fonts/octin stencil rg.otf"
font_hauteur = FontProperties(fname=font_path2)
font_hauteur_bold = FontProperties(fname=font_path3)
jours_font = FontProperties(fname=font_path)
NB_MAREE = 124
fancy_font = "fonts/AmaticSC-Bold.ttf"
regular_font = "Arial"
minutes_dans_journée = 1440
semaine = ["lu", "ma", "me", "je", "ve", "sa", "di"]
dossier_images = "processing_images"
dossier_ressources = "ressources"
size_factor = 0
marge_pointillets = 40
hauteur_jour = 1.9
hauteur_jour2 = 2.0
epaisseur_trait_jour = 1.0
limite_haut_coef = 95
limite_bas_coef = 35
header_size = 1.8
year = ""

# Configuration de la base de données
DB_NAME = "tides_database.db"

# Mapping des mois français vers leur numéro
MONTH_MAPPING = {
    'janvier': '01',
    'fevrier': '02',
    'mars': '03',
    'avril': '04',
    'mai': '05',
    'juin': '06',
    'juillet': '07',
    'aout': '08',
    'septembre': '09',
    'octobre': '10',
    'novembre': '11',
    'decembre': '12'
}

def init_database():
    """Initialise la base de données SQLite avec les tables nécessaires"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Vérifier si les tables existent déjà et ont des données
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ports'")
    ports_exists = cursor.fetchone()

    if ports_exists:
        # Vérifier si la table ports a des données
        cursor.execute('SELECT COUNT(*) FROM ports')
        ports_count = cursor.fetchone()[0]
        if ports_count > 0:
            print(f"[DB] Base déjà initialisée avec {ports_count} ports")
            conn.close()
            return

    # Supprimer les tables existantes si elles sont vides
    cursor.execute('DROP TABLE IF EXISTS tides')
    cursor.execute('DROP TABLE IF EXISTS ports')

    # Créer la table des ports
    cursor.execute('''
        CREATE TABLE ports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            port_name TEXT UNIQUE NOT NULL,
            port_code TEXT UNIQUE NOT NULL
        )
    ''')

    # Créer la table des données de marées (une ligne par jour)
    cursor.execute('''
        CREATE TABLE tides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            port_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            year TEXT NOT NULL,
            day INTEGER NOT NULL,
            day_name TEXT NOT NULL,
            tide1_type TEXT, tide1_time TEXT, tide1_height REAL, tide1_coef INTEGER,
            tide2_type TEXT, tide2_time TEXT, tide2_height REAL, tide2_coef INTEGER,
            tide3_type TEXT, tide3_time TEXT, tide3_height REAL, tide3_coef INTEGER,
            tide4_type TEXT, tide4_time TEXT, tide4_height REAL, tide4_coef INTEGER,
            moon_phase TEXT,
            saint_name TEXT,
            sunrise TEXT,
            sunset TEXT,
            FOREIGN KEY (port_id) REFERENCES ports (id)
        )
    ''')

    conn.commit()
    conn.close()
    print("[DB] Base de données initialisée")

def migrate_ports_to_db():
    """Migre les ports du fichier ports.txt vers la base de données"""
    ports_file = "ports.txt"
    if not os.path.exists(ports_file):
        ports_file = "old_ports.txt"  # Essayer l'ancien nom
        if not os.path.exists(ports_file):
            print("Fichier ports.txt ou old_ports.txt non trouvé")
            return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    with open(ports_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                # Les ports sont au format "nom-code"
                parts = line.split('-')
                if len(parts) >= 2:
                    port_name = '-'.join(parts[:-1])  # Tout sauf le dernier élément
                    port_code = parts[-1]            # Dernier élément

                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO ports (port_name, port_code)
                            VALUES (?, ?)
                        ''', (port_name, port_code))
                    except sqlite3.Error as e:
                        print(f"Erreur lors de l'insertion du port {port_name}: {e}")

    conn.commit()
    conn.close()
    print("Migration des ports terminée")

def migrate_tides_to_db():
    """Migre les fichiers txt de TIDES vers la base de données avec structure améliorée"""
    tides_dir = Path("TIDES")
    if not os.path.exists("TIDES"):
        tides_dir = Path("old_TIDES")  # Essayer l'ancien dossier
        if not os.path.exists("old_TIDES"):
            print("Dossier TIDES ou old_TIDES non trouvé")
            return

    # Si TIDES existe mais est presque vide, utiliser old_TIDES
    if os.path.exists("TIDES") and len(list(Path("TIDES").glob("tides-*.txt"))) < 10:
        if os.path.exists("old_TIDES"):
            tides_dir = Path("old_TIDES")
            print("Utilisation du dossier old_TIDES (TIDES semble vide)")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    migrated_count = 0

    for tide_file in tides_dir.glob("tides-*.txt"):
        filename = tide_file.name
        # Format attendu: tides-{port_name}-{port_code}-{month}-{year}.txt
        # Par exemple: tides-vieux-boucau-1052-aout-2025.txt
        parts = filename.replace("tides-", "").replace(".txt", "").split("-")

        # Trouver où commence le mois (dernier élément avant l'année)
        month_part = None
        port_code = None
        port_name_parts = []

        for i, part in enumerate(parts):
            if part in MONTH_MAPPING:
                month_part = part
                # Tout avant le mois est le nom du port
                port_name_parts = parts[:i]
                # Le dernier élément avant le mois est le code du port
                if i > 0:
                    port_code = parts[i-1]
                break

        if not month_part or not port_code:
            print(f"Format de fichier non reconnu: {filename}")
            continue

        port_name = '-'.join(port_name_parts)
        month_num = MONTH_MAPPING[month_part]
        year = parts[-1]  # Dernier élément est l'année

        try:
            with open(tide_file, "r", encoding="utf-8") as f:
                tide_data = f.read()

            # Sauvegarder avec la nouvelle structure
            save_tide_data_to_db(port_code, month_num, year, tide_data)
            migrated_count += 1

            if migrated_count % 50 == 0:
                print(f"Migration en cours... {migrated_count} fichiers traités")

        except Exception as e:
            print(f"Erreur lors de la migration du fichier {filename}: {e}")

    conn.close()
    print(f"Migration des données de marées terminée: {migrated_count} fichiers migrés")

def get_tide_data_from_db(port_code, month, year):
    """Récupère les données de marées depuis la base de données avec formatage correct"""
    print(f"[DB] Recherche en base: port_code='{port_code}', month='{month}', year='{year}'")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT t.day_name, t.day,
               t.tide1_type, t.tide1_time, t.tide1_height, t.tide1_coef,
               t.tide2_type, t.tide2_time, t.tide2_height, t.tide2_coef,
               t.tide3_type, t.tide3_time, t.tide3_height, t.tide3_coef,
               t.tide4_type, t.tide4_time, t.tide4_height, t.tide4_coef,
               t.moon_phase, t.saint_name, t.sunrise, t.sunset
        FROM tides t
        JOIN ports p ON t.port_id = p.id
        WHERE p.port_code = ? AND t.month = ? AND t.year = ?
        ORDER BY t.day
    ''', (port_code, month, year))

    results = cursor.fetchall()
    conn.close()

    print(f"[DB] {len(results)} jours trouvés en base de données")

    if not results:
        return None

    # Reconstituer le texte dans le format correct avec tri des marées par heure
    lines = []
    days_with_few_tides = []

    for row in results:
        day_name, day, *tide_data, moon_phase, saint_name, sunrise, sunset = row

        # Ligne du jour
        lines.append(f"{day_name} {day}")

        # Récupérer TOUTES les marées disponibles (pas seulement les 4 premiers groupes)
        all_tides = []
        for i in range(0, 16, 4):  # Parcourir les 4 groupes de marées
            tide_type, tide_time, tide_height, tide_coef = tide_data[i:i+4]
            if tide_type and tide_time and tide_height is not None:
                coef_str = f" {tide_coef}" if tide_coef else ""
                all_tides.append({
                    'type': tide_type,
                    'time': tide_time,
                    'height': tide_height,
                    'coef': tide_coef,
                    'line': f"Maree {tide_type} {tide_time} {tide_height}m{coef_str}"
                })

        # Trier les marées par heure
        def sort_tides_by_time(tide):
            heures, minutes = tide['time'].split('h')
            return int(heures) * 60 + int(minutes)

        all_tides.sort(key=sort_tides_by_time)

        # Vérification : au moins 3 marées par jour
        if len(all_tides) < 3:
            days_with_few_tides.append(f"Jour {day} ({day_name}): seulement {len(all_tides)} marées")
            print(f"[WARNING] Jour {day} ({day_name}): seulement {len(all_tides)} marées")

        # Note: Certains jours peuvent avoir des séquences haute/basse différentes
        # (ex: haute-basse-haute pour les jours avec seulement 3 marées)
        # Nous n'affichons plus de warnings pour ces cas normaux

        # Ajouter les lignes de marées triées
        for tide in all_tides:
            lines.append(tide['line'])

        # Info lune
        if moon_phase:
            lines.append(f"Lune : {moon_phase}")

        # Nom du saint
        if saint_name:
            lines.append(saint_name)

        # Info soleil
        if sunrise and sunset:
            lines.append(f"Soleil : {sunrise} {sunset}")

    # Afficher un résumé des problèmes trouvés
    if days_with_few_tides:
        print(f"[WARNING] {len(days_with_few_tides)} jours avec moins de 3 marées:")
        for warning in days_with_few_tides[:5]:  # Montrer les 5 premiers
            print(f"  {warning}")
        if len(days_with_few_tides) > 5:
            print(f"  ... et {len(days_with_few_tides) - 5} autres jours")

    return '\n'.join(lines)

def parse_tide_file_content(content):
    """Parse le contenu d'un fichier de marées et retourne une liste de jours structurés"""
    import re

    lines = content.strip().split('\n')
    days = []
    current_day = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Nouveau jour détecté (format: "lu 1", "ma 2", etc. ou "lundi 1", "mardi 2", etc.)
        parts = line.split()
        if len(parts) == 2:
            day_part = parts[0].lower()
            num_part = parts[1]
            if ((day_part in ['lu', 'ma', 'me', 'je', 've', 'sa', 'di'] or
                 day_part in ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']) and
                num_part.isdigit()):
                if current_day:
                    days.append(current_day)

                current_day = {
                    'day_name': day_part,
                    'day': int(num_part),
                    'tides': [],
                    'moon_phase': '',
                    'saint_name': '',
                    'sunrise': '',
                    'sunset': ''
                }
                i += 1
                continue

        # Marée détectée (deux formats possibles)
        line_lower = line.lower()
        if 'mar' in line_lower and ('haute' in line_lower or 'basse' in line_lower):
            if current_day:
                # Format d'une ligne: "Maree haute 08h30 3.8m 48"
                parts = line.split()
                if len(parts) >= 4:  # Format d'une ligne
                    tide_type = 'basse' if 'basse' in parts[1] else 'haute'
                    tide_time = parts[2]
                    height_part = parts[3]
                    tide_height = float(height_part[:-1]) if height_part.endswith('m') else None
                    tide_coef = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else None

                    current_day['tides'].append({
                        'type': tide_type,
                        'time': tide_time,
                        'height': tide_height,
                        'coef': tide_coef
                    })
                else:
                    # Format multi-ligne du site web (ancien format)
                    tide_type = 'basse' if 'basse' in line_lower else 'haute'

                    # Les informations suivantes sont sur les lignes suivantes
                    tide_time = None
                    tide_height = None

                    # Chercher l'heure sur la ligne suivante
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        import re
                        time_match = re.search(r'(\d{1,2}h\d{1,2})', next_line)
                        if time_match:
                            tide_time = time_match.group(1)
                            i += 1  # Consommer la ligne de l'heure

                    # Chercher la hauteur sur la ligne suivante
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        height_match = re.search(r'(\d+\.\d+)m', next_line)
                        if height_match:
                            tide_height = float(height_match.group(1))
                            i += 1  # Consommer la ligne de la hauteur

                    # Ajouter la marée si on a au moins le type et l'heure
                    if tide_time:
                        current_day['tides'].append({
                            'type': tide_type,
                            'time': tide_time,
                            'height': tide_height,
                            'coef': None  # Sera rempli plus tard
                        })

        # Coefficients isolés (après toutes les marées du jour)
        elif line.isdigit() and 20 <= int(line) <= 120 and current_day and current_day['tides']:
            # Assigner ce coefficient à la première marée qui n'en a pas
            for tide in current_day['tides']:
                if tide['coef'] is None:
                    tide['coef'] = int(line)
                    break

        # Info lune
        elif line.lower().startswith('lune'):
            if current_day:
                if line.lower().startswith('lune :'):
                    # Format: "Lune : Phase lunaire"
                    current_day['moon_phase'] = line[7:].strip()  # Tout après "Lune : "
                else:
                    # Format multi-ligne: "Lune" puis "Lune gibbeuse croissante" sur la ligne suivante
                    if i + 1 < len(lines):
                        moon_line = lines[i + 1].strip()
                        if moon_line.lower().startswith('lune'):
                            current_day['moon_phase'] = moon_line
                            i += 1  # Consommer la ligne de la phase lunaire

        # Nom du saint
        elif line.startswith(('Saint ', 'Sainte ')):
            if current_day:
                current_day['saint_name'] = line.strip()

        # Info soleil (lever/coucher)
        elif line.lower() == 'lever':
            if current_day and i + 2 < len(lines):
                # Format: "Lever" puis heure puis "Coucher" puis heure
                sunrise_line = lines[i + 1].strip()
                if 'coucher' in lines[i + 2].lower():
                    sunset_line = lines[i + 3].strip() if i + 3 < len(lines) else ''
                    current_day['sunrise'] = sunrise_line
                    current_day['sunset'] = sunset_line
                    i += 3  # Consommer les lignes de soleil

        i += 1

    # Ajouter le dernier jour
    if current_day:
        days.append(current_day)

    return days

def save_tide_data_to_db(port_code, month, year, tide_data):
    """Sauvegarde les données de marées dans la base de données"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Récupérer l'ID du port
        cursor.execute('SELECT id FROM ports WHERE port_code = ?', (port_code,))
        port_result = cursor.fetchone()
        if not port_result:
            print(f"[ERREUR] Port {port_code} non trouvé dans la base")
            conn.close()
            return

        port_id = port_result[0]

        # Parser les données du fichier avec gestion d'erreur
        try:
            days = parse_tide_file_content(tide_data)
            print(f"[DEBUG] Parser a trouvé {len(days)} jours de données")
        except Exception as e:
            print(f"[ERREUR] Impossible de parser les données: {e}")
            print(f"[DEBUG] Contenu problématique: {tide_data[:200]}...")
            conn.close()
            return

        if not days:
            print(f"[WARNING] Aucune donnée de marée valide trouvée à sauvegarder")
            conn.close()
            return

        # Insérer chaque jour avec gestion d'erreur individuelle
        saved_count = 0
        for day_data in days:
            try:
                # Préparer les données des marées (jusqu'à 4 marées)
                tide_data = {}
                for idx, tide in enumerate(day_data['tides'][:4]):  # Maximum 4 marées
                    tide_num = idx + 1
                    tide_data[f'tide{tide_num}_type'] = tide.get('type')
                    tide_data[f'tide{tide_num}_time'] = tide.get('time')
                    tide_data[f'tide{tide_num}_height'] = tide.get('height')
                    tide_data[f'tide{tide_num}_coef'] = tide.get('coef')

                # Validation basique des données
                if not isinstance(day_data.get('day'), int) or not day_data.get('day_name'):
                    print(f"[WARNING] Données invalides pour jour: {day_data}")
                    continue

                # Insérer dans la base (25 valeurs pour 25 colonnes, id est auto-incrémenté)
                cursor.execute('''
                    INSERT INTO tides (
                        port_id, month, year, day, day_name,
                        tide1_type, tide1_time, tide1_height, tide1_coef,
                        tide2_type, tide2_time, tide2_height, tide2_coef,
                        tide3_type, tide3_time, tide3_height, tide3_coef,
                        tide4_type, tide4_time, tide4_height, tide4_coef,
                        moon_phase, saint_name, sunrise, sunset
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    port_id, month, year, day_data['day'], day_data['day_name'],
                    tide_data.get('tide1_type'), tide_data.get('tide1_time'),
                    tide_data.get('tide1_height'), tide_data.get('tide1_coef'),
                    tide_data.get('tide2_type'), tide_data.get('tide2_time'),
                    tide_data.get('tide2_height'), tide_data.get('tide2_coef'),
                    tide_data.get('tide3_type'), tide_data.get('tide3_time'),
                    tide_data.get('tide3_height'), tide_data.get('tide3_coef'),
                    tide_data.get('tide4_type'), tide_data.get('tide4_time'),
                    tide_data.get('tide4_height'), tide_data.get('tide4_coef'),
                    day_data.get('moon_phase'), day_data.get('saint_name'),
                    day_data.get('sunrise'), day_data.get('sunset')
                ))

                saved_count += 1

            except Exception as e:
                print(f"[ERREUR] Impossible de sauvegarder le jour {day_data.get('day', 'inconnu')}: {e}")
                continue

        conn.commit()
        conn.close()

        print(f"[OK] {saved_count}/{len(days)} jours sauvegardés en base pour {port_code}-{month}-{year}")

    except Exception as e:
        print(f"[ERREUR] Erreur générale lors de la sauvegarde en base: {e}")
        return

    finally:
        try:
            conn.close()
        except:
            pass

def ajouter_donnees_manuellement(port_code, month, year, tide_text):
    """Permet d'ajouter manuellement des données de marées à la base

    Args:
        port_code (str): Code du port (ex: '1052')
        month (str): Mois au format MM (ex: '01')
        year (str): Année (ex: '2026')
        tide_text (str): Texte brut des données de marées
    """
    print(f"[MANUEL] Ajout de données pour {port_code}-{month}-{year}")

    try:
        save_tide_data_to_db(port_code, month, year, tide_text)
        print(f"[SUCCÈS] Données ajoutées à la base pour {port_code}-{month}-{year}")
        return True
    except Exception as e:
        print(f"[ERREUR] Impossible d'ajouter les données: {e}")
        return False


def check_db_data():
    """Vérifie le contenu de la base de données"""
    print("[CHECK] Vérification du contenu de la base de données...")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Vérifier les ports
    cursor.execute('SELECT COUNT(*) FROM ports')
    ports_count = cursor.fetchone()[0]
    print(f"[CHECK] Nombre de ports: {ports_count}")

    cursor.execute('SELECT port_name, port_code FROM ports LIMIT 5')
    ports = cursor.fetchall()
    for port in ports:
        print(f"[CHECK] Port: {port[0]} ({port[1]})")

    # Vérifier les données de marées
    cursor.execute('SELECT COUNT(*) FROM tides')
    tides_count = cursor.fetchone()[0]
    print(f"[CHECK] Nombre total de jours de marées: {tides_count}")

    # Statistiques par port
    cursor.execute('''
        SELECT p.port_name, p.port_code, COUNT(t.id) as days_count
        FROM ports p
        LEFT JOIN tides t ON p.id = t.port_id
        GROUP BY p.id, p.port_name, p.port_code
        ORDER BY days_count DESC
    ''')
    port_stats = cursor.fetchall()

    print("[CHECK] Statistiques par port:")
    for port_name, port_code, days_count in port_stats:
        print(f"[CHECK]   {port_name} ({port_code}): {days_count} jours")

    # Vérifier la structure d'un exemple de données
    cursor.execute('''
        SELECT t.day_name, t.day, t.tide1_type, t.tide1_time, t.tide1_height, t.tide1_coef,
               t.moon_phase, t.saint_name, t.sunrise, t.sunset
        FROM tides t
        JOIN ports p ON t.port_id = p.id
        WHERE p.port_code = ?
        ORDER BY t.day
        LIMIT 3
    ''', (ports[0][1],) if ports else ('1052',))

    sample_data = cursor.fetchall()
    if sample_data:
        print("[CHECK] Exemple de données pour le premier port:")
        for row in sample_data:
            print(f"[CHECK]   Jour: {row[0]} {row[1]}, Marée1: {row[2]} {row[3]} {row[4]}m {row[5]}, Lune: {row[6]}, Saint: {row[7]}, Soleil: {row[8]} {row[9]}")

    conn.close()
    print("[CHECK] Vérification terminée")

#TODO essayer de rendre la taille de tout modifiable de facon harmonieuse via GUI. les espaces entre les machins et les tailles de police surtout.
# éventuellement les polices aussi. Et les seuils de marée rouge vert. 




def get_days_in_month(year, month):
    """Calcule le nombre de jours dans un mois donné

    Args:
        year (int): Année
        month (int): Mois (1-12)

    Returns:
        int: Nombre de jours dans le mois
    """
    import calendar
    return calendar.monthrange(year, month)[1]

def ensure_port_in_db(port_name, port_code):
    """S'assurer qu'un port existe dans la base de données"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Vérifier si le port existe
        cursor.execute('SELECT id FROM ports WHERE port_code = ?', (port_code,))
        existing = cursor.fetchone()

        if not existing:
            # Ajouter le port s'il n'existe pas
            cursor.execute('INSERT INTO ports (port_name, port_code) VALUES (?, ?)',
                         (port_name, port_code))
            conn.commit()
            print(f"[DB] Port {port_name} ({port_code}) ajouté à la base de données")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"[ERREUR] Impossible d'ajouter le port: {e}")
        return False

def check_complete_month_data(port_code, month, year):
    """Vérifie si la base de données contient tous les jours du mois

    Args:
        port_code (str): Code du port
        month (str): Mois au format MM
        year (str): Année

    Returns:
        tuple: (has_data, is_complete, days_count, expected_days)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        # Compter le nombre de jours dans la base
        cursor.execute('''
            SELECT COUNT(DISTINCT day) as days_count
            FROM tides t
            JOIN ports p ON t.port_id = p.id
            WHERE p.port_code = ? AND t.month = ? AND t.year = ?
        ''', (port_code, month, year))

        result = cursor.fetchone()
        days_count = result[0] if result else 0

        # Calculer le nombre de jours attendu dans le mois
        expected_days = get_days_in_month(int(year), int(month))

        has_data = days_count > 0
        # Un mois est considéré complet s'il a au moins 80% des jours
        # (certains jours peuvent manquer de marées)
        is_complete = days_count >= expected_days * 0.8

        print(f"[CHECK] Port {port_code}-{month}-{year}: {days_count}/{expected_days} jours ({'complet' if is_complete else 'incomplet'})")

        return has_data, is_complete, days_count, expected_days

    except Exception as e:
        print(f"[ERREUR] Erreur lors de la vérification des données: {e}")
        return False, False, 0, 0
    finally:
        conn.close()

def convert_scraper_data_to_text(scraped_data):
    """Convertit les données du scrapper en format texte pour la base de données

    Args:
        scraped_data (list): Liste des données de marées du scrapper

    Returns:
        str: Données formatées en texte
    """
    if not scraped_data:
        return ""

    lines = []

    for day_data in scraped_data:
        # Jour de la semaine et numéro
        day_name = day_data.get('date', '').split('-')[-1]  # Extraire le jour du format YYYY-MM-DD

        # Pour simplifier, on utilise un mapping basique des jours
        # En réalité, il faudrait calculer le jour de la semaine depuis la date
        day_num = int(day_data.get('date', '').split('-')[-1])

        # Mapping des jours (approximation simple)
        jours_abbr = ['di', 'lu', 'ma', 'me', 'je', 've', 'sa']
        # Pour une vraie implémentation, il faudrait utiliser datetime pour déterminer le jour
        # Ici on utilise une approximation
        day_name_abbr = jours_abbr[day_num % 7]  # Approximation simple

        lines.append(f"{day_name_abbr} {day_num}")

        # Marées du jour
        marees = day_data.get('marees', [])
        for maree in marees:
                    tide_type = maree.get('type', '')
                    tide_time = maree.get('heure', '').replace(':', 'h')
                    tide_height = maree.get('hauteur', '').replace('mm', 'm')  # Corriger le format mm -> m
                    tide_coef = maree.get('coefficient', '')

                    coef_str = f" {tide_coef}" if tide_coef else ""
                    lines.append(f"Maree {tide_type} {tide_time} {tide_height}{coef_str}")

        # Phase lunaire
        lunar_phase = marees[0].get('phase_lunaire', '') if marees else ''
        if lunar_phase:
            lines.append(f"Lune : {lunar_phase}")

        # Pour l'instant, on ne gère pas les saints et heures de soleil
        # Ces informations ne sont pas extraites par le scrapper actuel

    return '\n'.join(lines)

def cree_dossier_images():
    if os.path.exists(dossier_images):
        shutil.rmtree(dossier_images)
    os.mkdir(dossier_images)
    if os.path.exists(dossier_ressources):
        shutil.rmtree(dossier_ressources)
    os.mkdir(dossier_ressources)

def aligne_basse(chaine):
    # Créer un modèle de regex pour trouver "Maree basse" suivie de la prochaine lettre "M" ou "L"
    modele = re.compile(r"Maree basse(.*?[ML])", re.DOTALL)
    # Utiliser la méthode sub() pour supprimer les retours à la ligne dans la correspondance
    chaine_modifiee = modele.sub(lambda match: "Maree basse" + match.group(1).replace('\n', ' '), chaine)
    return chaine_modifiee

def aligne_haute(chaine):
    # Créer un modèle de regex pour trouver "Maree basse" suivie de la prochaine lettre "M" ou "L"
    modele = re.compile(r"Maree haute(.*?[ML])", re.DOTALL)
    # Utiliser la méthode sub() pour supprimer les retours à la ligne dans la correspondance
    chaine_modifiee = modele.sub(lambda match: "Maree haute" + match.group(1).replace('\n', ' '), chaine)
    return chaine_modifiee

def ecrire_texte_dans_csv(texte, nom_fichier):
    with open(nom_fichier, 'w') as fichier:
        fichier.write(texte)

def clean (soup) :
    """Nettoie et extrait le texte des données de marées depuis la soupe HTML"""
    print(f"[DEBUG] Parsing HTML - titre de la page: {soup.title.get_text() if soup.title else 'Pas de titre'}")

    # Essayer différentes approches pour extraire les données

    # 1. Chercher tous les spans (ancienne méthode)
    all_spans = soup.find_all('span')
    print(f"[DEBUG] Nombre de spans trouvés: {len(all_spans)}")

    if all_spans:
        span_contents = [span.get_text().strip() for span in all_spans if span.get_text().strip()]
        print(f"[DEBUG] Contenu des spans (premiers 5): {span_contents[:5]}")

        # Essayer de reconstituer le format attendu
        cleaned_text = ', '.join(span_contents)
        return cleaned_text

    # 2. Si pas de spans, chercher d'autres éléments
    print("[DEBUG] Pas de spans trouvés, essayer autres éléments...")

    # Chercher des divs ou autres conteneurs
    containers = soup.find_all(['div', 'p', 'td', 'li'])
    print(f"[DEBUG] Nombre de conteneurs trouvés: {len(containers)}")

    if containers:
        container_texts = [c.get_text().strip() for c in containers if c.get_text().strip()]
        print(f"[DEBUG] Contenu des conteneurs (premiers 5): {container_texts[:5]}")
        cleaned_text = ', '.join(container_texts)
        return cleaned_text

    # 3. En dernier recours, tout le texte de la page
    print("[DEBUG] Utilisation du texte brut de la page...")
    try:
        all_text = soup.get_text()
        print(f"[DEBUG] Longueur du texte brut: {len(all_text)}")
        print(f"[DEBUG] Aperçu du texte brut: {repr(all_text[:200])}...")
        return all_text
    except Exception as e:
        print(f"[ERREUR] Impossible d'extraire le texte: {e}")
        return f"Erreur d'extraction du texte: {e}"

def remove_lines_until_marker(text, marker):
    lines = text.split("\n")
    output_lines = []
    found_marker = False
    for line in lines:
        if found_marker:
            output_lines.append(line)
        if marker in line:
            found_marker = True
    result = "\n".join(output_lines)
    return result

def remove_lines_after_marker(text, marker):
    lines = text.split("\n")
    output_lines = []
    found_marker = False
    for line in lines:
        if marker in line:
            found_marker = True
        if not found_marker:
            output_lines.append(line)
    result = "\n".join(output_lines)
    return result

def ligne_commence_par_mot(liste_mots, ligne):
    """
    Vérifie si une ligne de texte commence par un des mots de la liste donnée.

    Paramètres :
        liste_mots : liste de chaînes de caractères
        ligne : chaîne de caractères

    Retourne :
        bool : True si la ligne commence par un des mots de la liste,
               False sinon
    """
    for mot in liste_mots:
        if ligne.startswith(mot):
            return True
    return False

def calculer_angle_entre_points(point1, point2):
    # Extraire les coordonnées x et y de chaque point
    x1, y1 = point1
    x2, y2 = point2
    # Calculer la différence entre les coordonnées x et y
    diff_x = x2 - x1
    diff_y = y2 - y1
    # Calculer l'angle en radians en utilisant atan2
    angle_radians = math.atan2(diff_y, diff_x)
    # Convertir l'angle de radians à degrés
    angle_degrees = math.degrees(angle_radians)
    # Assurer que l'angle est positif (entre 0 et 360 degrés)
    angle_degrees = (angle_degrees + 180) % 360 - 180
    return angle_degrees

def plot_line_with_dashes(x_points, y_points):
    linestyle = '--'
    x_points[0] = x_points[0]+marge_pointillets
    x_points[1] = x_points[1]-marge_pointillets
    plt.plot(x_points, y_points, linestyle=linestyle, color='black', linewidth=epaisseur_trait_jour )

def convert_to_minutes(heure_string):
    heures, minutes = heure_string.split('h')
    return int(heures) * 60 + int(minutes)

def convert_to_jours(jour_string):
    jour, nb = jour_string.split(' ')
    return int(nb)*minutes_dans_journée

def get_image_creation_time(image_path):
    return os.path.getctime(image_path)

def stack_images_in_order(input_folder, output_filename):
    image_paths = sorted(Path(input_folder).glob("*.png"), key=get_image_creation_time)
    stacked_images = []

    for image_path in image_paths:
        image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)  # Inclure le canal alpha.
        stacked_images.append(image)

    max_width = max(image.shape[1] for image in stacked_images)
    total_height = sum(image.shape[0] for image in stacked_images)

    stacked_image = np.zeros((total_height, max_width, stacked_images[0].shape[2]), dtype=np.uint8)

    current_y = 0
    for image in stacked_images:
        h, w, _ = image.shape
        x_offset = (max_width - w) // 2  # Calculer le décalage pour centrer l'image
        stacked_image[current_y:current_y + h, x_offset:x_offset + w] = image
        current_y += h

    cv2.imwrite("ressources/" + output_filename, stacked_image)

def nettoyage_page_web(text):
    t = clean(text)
    t = t.replace(',', '\n')
    t = unidecode(t)
    t = output_text = remove_lines_until_marker(t, "101-129")
    t = output_text = remove_lines_until_marker(t, "101-129")
    t = output_text = remove_lines_after_marker(t, "3201")
    t = t.replace("\n ", "\n")[1:]
    t = t.replace("Lune\n", "Lune : ")
    t = t.replace("Saint\nSaint", "Saint")
    t = aligne_basse(t)
    t = t.replace(" Maree haute", "\nMaree haute")
    t = t.replace(" Lune :", "\nLune :")
    t = aligne_haute(t)
    t = t.replace(" Mar", "\nMar")
    t = t.replace(" Lune :", "\nLune :")
    t = t.replace("\nCoucher\n", " ")
    t = t.replace("Lever\n", "Soleil : ")
    t = t.replace("lundi","lu")
    t = t.replace("mardi","ma")
    t = t.replace("mercredi", "me")
    t = t.replace("jeudi","je")
    t = t.replace("vendredi", "ve")
    t = t.replace("samedi", "sa")
    t = t.replace("dimanche", "di")
    t = t.replace("Lune gibbeuse decroissante", "")
    t = t.replace("Lune gibbeuse croissante", "")
    t = t.replace("Premier croissant de lune", "")
    t = t.replace("Dernier croissant de lune", "")
    t = t.replace("Premier quartier de lune", "PR_QRT")
    t = t.replace("Dernier quartier de lune", "DR_QRT")
    t = t.replace("Pleine lune", "PL_LUNE")
    t = t.replace("Nouvelle lune", "NV_LUNE")
    return t

def write_text_on_image(image_path, text, angle, position, font_name, font_size, text_color = (255,255,255,255)):
    background_color=(0,0,0,0)
    im = Image.open(image_path)
    font = ImageFont.truetype(font_name, font_size)
    
    # Création d'une nouvelle image pour écrire le texte
    txt = Image.new("RGBA", (im.height,im.height), background_color)
    d = ImageDraw.Draw(txt)
    d.text((size_factor, 0), text, font=font, fill=None)

    # Rotation de l'image contenant le texte
    w = txt.rotate(angle, expand=1)
    w = w.convert("RGBA")
    # Superposition de l'image contenant le texte sur l'image originale
    im.paste(w, position, w)
    im.save(image_path)

def draw(url, port, month, year, nom):
    lines = recuperation_et_sauvegarde_url(url, port, month, year).split('\n')
    #le tableau stoke les infos qui nous seront utiles pour faire les graphes.
    # sous la forme tableau de tableaux  ['me 22' '22h26' '3.16m' '35' 'Dernier quartier de lune']
    tab = np.empty((NB_MAREE, 5), dtype=object)
    i = 0
    date = "rien 0"
    for l in lines:
        
        if ligne_commence_par_mot(semaine, l):
            date = l
        if l.startswith("Maree"):
            tab[i][0] = date
            l = l[12:]
            tmp = l.split(" ")
            tab[i][1] = tmp[0]
            tab[i][2] = tmp[1]
            if len(tmp)==3 :
                tab[i][3] = tmp[2]
            i=i+1
        if l.startswith("Lune"):
            tab[i-1][4] = l[7:]


    # Liste des hauteurs 
    hauteurs = np.zeros(NB_MAREE)
    for i in range(len(hauteurs)):
        if tab[i][2] is not None :
            hauteurs[i] = float(tab[i][2][:-1])

    hauteurs = np.delete(hauteurs, np.where(hauteurs == 0.0))
    moyenne_hauteur = np.mean(hauteurs)
    heures = np.empty((NB_MAREE), dtype=object)
    for i in range(len(hauteurs)):
        if tab[i][1] is not None :
            heures[i] = tab[i][1]
    heures = np.delete(heures, np.where(heures == None))

    minutes = np.zeros(NB_MAREE)
    for i in range(len(heures)):
        minutes[i] = convert_to_minutes(heures[i])+convert_to_jours(tab[i][0])
    minutes = np.delete(minutes, np.where(minutes == 0))


    coeficients = np.empty((NB_MAREE), dtype=object)
    for i in range(len(coeficients)):
        if tab[i][3] is not None :
            coeficients[i] = (tab[i][3])
    
    lunes = np.empty((NB_MAREE), dtype=object)
    for i in range(len(lunes)):
        if tab[i][4] is not None :
            lunes[i] = (tab[i][4])

    # Créer une liste d'abscisses pour les hauteurs
    abscisses = [i*5 for i in range(len(hauteurs))]

    # Créer la figure et les axes
    fig, ax = plt.subplots()

    # Tracer les hauteurs sous forme de segments noirs inclinés
    ax.plot(minutes, hauteurs, color='black', linewidth=6)


    # la ca écrit les hauteurs d'eau
    for x, y in zip(minutes, hauteurs):
        if y > moyenne_hauteur :
            ax.text(x, y+0.2, str(y)+"m", ha='center', va='bottom', fontproperties=font_hauteur, fontsize=15, color='white')
        else :
            ax.text(x, y-0.2, str(y)+"m", ha='center', va='top', fontproperties=font_hauteur, fontsize=15, color='white')
    line_index = 0
    current_day = "t"
    previous_day = "r"
    hauteur_précédente =  0.0
    hauteur_précédente_2 = 0.0
    

    décalage_hauteur_petits_traits = 1.45

    def insere_lune(x, y, phase):
        # Appliquer le même nettoyage que pour le texte (lignes 729-738)
        # pour déterminer si cette phase doit être ignorée
        cleaned_phase = phase
        cleaned_phase = cleaned_phase.replace("Lune gibbeuse décroissante", "")
        cleaned_phase = cleaned_phase.replace("Lune gibbeuse croissante", "")
        cleaned_phase = cleaned_phase.replace("Premier croissant de lune", "")
        cleaned_phase = cleaned_phase.replace("Dernier croissant de lune", "")
        cleaned_phase = cleaned_phase.replace("Premier quartier de lune", "PR_QRT")
        cleaned_phase = cleaned_phase.replace("Dernier quartier de lune", "DR_QRT")
        cleaned_phase = cleaned_phase.replace("Pleine lune", "PL_LUNE")
        cleaned_phase = cleaned_phase.replace("Nouvelle lune", "NV_LUNE")

        # Si la phase est vide après nettoyage, l'ignorer complètement
        if not cleaned_phase.strip():
            return

        image_path = cleaned_phase.strip() + '.png'
        img = mpimg.imread("ressources/"+image_path)
        # Spécifiez la position de l'image (en coordonnées de données)
        x_position = x
        y_position = y
        imagebox = OffsetImage(img, zoom=0.1)  # Vous pouvez ajuster le zoom selon vos besoins
        ab = AnnotationBbox(imagebox, (x_position, y_position), frameon=False)
        ax.add_artist(ab)


    def operation(a, b, signe):
        if signe ==1:
            return a+b
        return a-b

    def draw_stuff(hauteur_to_update, updown, day):
       """
       Draws text and lines on a plot based on the given parameters.

       Args:
           hauteur_to_update (float): The height value to update.
           updown (int): 1 = marée haute, -1 = maree basse.
           day (str): The current day.
       Returns:
           tuple: A tuple containing the current day and the updated height value.
       """
       if line_index <= 1 and line_index+4 < len(hauteurs):
           hauteur_to_update = operation(hauteurs[line_index+4], décalage_hauteur_petits_traits, updown)
       #ecrit l'heure de la marée
       ax.text(x, operation(y, 0.7 if updown == 1 else 1.2, updown), h, ha='center', va='bottom', fontproperties=font_hauteur_bold, fontsize=15, color='white', weight='bold')
       jour = tab[line_index][0]
       if day != jour:
           pt1 = (x, hauteurs[line_index])
           pt2 = (0,0)
           if line_index+4 < len(minutes) and line_index+4 < len(hauteurs):
               pt2 = (minutes[line_index+4], hauteurs[line_index+4])
           # elif line_index<len(minutes):
           #     pt2 = (minutes[line_index], hauteurs[line_index+2])
           else:
               pt2 = (minutes[line_index], hauteurs[line_index])
           angle = calculer_angle_entre_points(pt1, pt2)
           jour_to_write, date_to_write =  tab[line_index][0].split(" ")
           nom_jour = jour_to_write[0].upper()+date_to_write
           #ecrit le nom du jour

           if line_index+2 < len(hauteurs):
               if updown:
                   ax.text((0.28+minutes[line_index]//minutes_dans_journée)*minutes_dans_journée, operation(max(hauteurs[line_index+2], hauteurs[line_index]), hauteur_jour if updown == 1 else hauteur_jour2, updown), nom_jour, fontproperties=jours_font, rotation=angle*650,
 ha='center', va='center', color='black', fontsize=23)
               else:
                   ax.text((0.28+minutes[line_index]//minutes_dans_journée)*minutes_dans_journée, operation(min(hauteurs[line_index+2], hauteurs[line_index]), hauteur_jour if updown == 1 else hauteur_jour2, updown), nom_jour, fontproperties=jours_font, rotation=angle*650,
 ha='center', va='center', color='black', fontsize=23)
           else:
               ax.text((0.28+minutes[line_index]//minutes_dans_journée)*minutes_dans_journée, operation(hauteurs[line_index], hauteur_jour if updown == 1 else hauteur_jour2, updown), nom_jour, fontproperties=jours_font, rotation=angle*650, ha='center', va='center',
 color='black', fontsize=23)
           x_points = [minutes[line_index]//minutes_dans_journée*minutes_dans_journée, ((minutes[line_index]//minutes_dans_journée)+1)*minutes_dans_journée]
           if updown<0:
               if x_points[1] == 0.0:
                   x_points[1] = x_points[0]
           if line_index+4 < len(hauteurs):
               y_points = [operation(hauteurs[line_index],décalage_hauteur_petits_traits, updown), operation(hauteurs[line_index+4], décalage_hauteur_petits_traits, updown)]
               if line_index>1:
                   y_points = [hauteur_to_update, operation(hauteurs[line_index+4],décalage_hauteur_petits_traits, updown)]
                   hauteur_to_update = operation(hauteurs[line_index+4],décalage_hauteur_petits_traits, updown)
           elif line_index+2<len(hauteurs):
               y_points = [operation(hauteurs[line_index],décalage_hauteur_petits_traits, updown), operation(hauteurs[line_index+2],décalage_hauteur_petits_traits, updown)]
               if line_index>1:
                   y_points = [hauteur_to_update, operation(hauteurs[line_index+2],décalage_hauteur_petits_traits, updown)]
                   hauteur_to_update = operation(hauteurs[line_index+2],décalage_hauteur_petits_traits, updown)
           else:
               y_points = [operation(hauteurs[line_index],décalage_hauteur_petits_traits, updown), operation(hauteurs[line_index],décalage_hauteur_petits_traits, updown)]
               if line_index>1:
                   y_points = [hauteur_to_update, operation(hauteurs[line_index],décalage_hauteur_petits_traits, updown)]
                   hauteur_to_update = operation(hauteurs[line_index],décalage_hauteur_petits_traits, updown)
           plot_line_with_dashes(x_points, y_points)
       return jour, hauteur_to_update

    for x, y, h in zip(minutes, hauteurs, heures):
        if y > moyenne_hauteur:
            current_day, hauteur_précédente = draw_stuff(hauteur_précédente, 1, current_day)
        else:
            previous_day, hauteur_précédente_2 = draw_stuff(hauteur_précédente_2, -1, previous_day)
        line_index = line_index+1

    last_coef = 0
    for i in range(5):
        if coeficients[i] is not None and int(coeficients[i]) >10:
            last_coef = coeficients[i]   
    
    def couleur_coefficient(couleur):
        #ecrit le coefficient
        ax.text(x, moyenne_hauteur-0.5, str(last_coef), ha='center', va='bottom', fontname=regular_font, fontsize=18, color=couleur, weight='bold')
    for x, y, c in zip(minutes, hauteurs, coeficients):
        if c is not None and int(c) > 10 :
            last_coef = c
        if y > moyenne_hauteur :
            if int(last_coef) > limite_haut_coef :
                couleur_coefficient('red')
            elif int(last_coef) < limite_bas_coef :
                couleur_coefficient('forestgreen')
            else :
                couleur_coefficient('black')
    
    #on va mettre la lune là ou il faut
    compteur = 0
    for x, y, l in zip(minutes, hauteurs, lunes):
        if l is not None and l != "":
            if y < moyenne_hauteur:
                lunes[compteur+1] = lunes[compteur]
            else:
                insere_lune(x-375, moyenne_hauteur+0.35, l)
        compteur = compteur+1

    plt.axis('off')
    largeur_pouces = 80
    hauteur_pouces = 6
    fig = plt.gcf()
    fig.set_size_inches(largeur_pouces, hauteur_pouces)
    plt.savefig(nom, transparent=True, dpi=size_factor, bbox_inches='tight', format='png')
    plt.close()

    #ici on élargit l'image (on rajoute une zone a gauche) pour avoir la place plus tard d'écrire le mois
    space_factor = 0.7
    image = cv2.imread(nom, cv2.IMREAD_UNCHANGED)
    height, width, _ = image.shape
    padded_image = np.zeros((height, (width+int(space_factor*height)), 4), dtype=np.uint8)
    # Copier l'image d'entrée à droite avec un espace vide à gauche
    padded_image[:, int(space_factor*height):] = image
    cv2.imwrite(nom, padded_image)
    #et on écrit le mois
    write_text_on_image(nom, nom[18:-9], 30, (size_factor, size_factor//3), fancy_font, int(size_factor*1.25))


def create_moon_image():
    """Génère les images de phases de lune en ignorant complètement certaines phases"""

    def draw_images(phase, size=200):
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        center = size // 2
        radius = center - 1
        w = size//20

        if phase == 'PL_LUNE':
            draw.ellipse((center - radius, center - radius, center + radius, center + radius), fill='white', outline='black', width=w)
        elif phase == 'NV_LUNE':
            draw.ellipse((center - radius, center - radius, center + radius, center + radius), fill='black', outline='black', width=w)
        elif phase == 'PR_QRT':
            draw.ellipse((center - radius, center - radius, center + radius, center + radius), fill='white', outline='black', width=w)
            draw.rectangle((center, 0, size, size), fill=(0, 0, 0, 0))
            draw.line((center, 0, center, size), width=w, fill='black')
        elif phase == 'DR_QRT':
            draw.ellipse((center - radius, center - radius, center + radius, center + radius), fill='white', outline='black', width=w)
            draw.rectangle((0, 0, center, size), fill=(0, 0, 0, 0))
            draw.line((center, 0, center, size), width=w, fill='black')
        image.save("ressources/" + phase+ '.png')
        return image

    # Utiliser la même logique que pour le texte (lignes 729-738) pour déterminer quelles phases garder
    # Tester avec un texte contenant toutes les phases possibles
    test_phases = [
        "Lune gibbeuse décroissante",
        "Lune gibbeuse croissante",
        "Premier croissant de lune",
        "Dernier croissant de lune",
        "Premier quartier de lune",
        "Dernier quartier de lune",
        "Pleine lune",
        "Nouvelle lune"
    ]

    # Appliquer les mêmes remplacements que dans la fonction de nettoyage du texte
    phases_to_generate = []
    for phase in test_phases:
        cleaned = phase
        cleaned = cleaned.replace("Lune gibbeuse décroissante", "")
        cleaned = cleaned.replace("Lune gibbeuse croissante", "")
        cleaned = cleaned.replace("Premier croissant de lune", "")
        cleaned = cleaned.replace("Dernier croissant de lune", "")
        cleaned = cleaned.replace("Premier quartier de lune", "PR_QRT")
        cleaned = cleaned.replace("Dernier quartier de lune", "DR_QRT")
        cleaned = cleaned.replace("Pleine lune", "PL_LUNE")
        cleaned = cleaned.replace("Nouvelle lune", "NV_LUNE")

        # Si le résultat n'est pas vide, c'est une phase à garder
        if cleaned.strip():
            phases_to_generate.append(cleaned.strip())

    print(f"[MOON] Phases de lune à générer : {phases_to_generate}")

    # Générer les images seulement pour les phases qui ne sont pas ignorées
    for phase in phases_to_generate:
        draw_images(phase)

def combine_images (image1, image2):
    if image1.shape != image2.shape:
        raise ValueError("Les images doivent avoir la même taille et le même nombre de canaux.")

    # Extraire les canaux d'images (B, G, R, alpha)
    b, g, r, alpha = cv2.split(image1)

    # Appliquer une pondération alpha aux canaux BGR de l'image 1
    image1_bgr = cv2.merge((b, g, r))
    overlay_image = cv2.addWeighted(image1_bgr, 1 - alpha / 255.0, image2, alpha / 255.0, 0)

    # Recoller le canal alpha à l'image résultante
    b, g, r = cv2.split(overlay_image)
    overlay_with_alpha = cv2.merge((b, g, r, alpha))

    # Enregistrer l'image résultante
    cv2.imwrite('image_superposee.png', overlay_with_alpha)

def image_vide(nom):
    print(nom)
    """Crée une image vide en RGBA et l'enregistre sous le nom spécifié.

    Args:
        nom (str): Nom du fichier de sortie.
        size_factor (int): Facteur de taille pour l'image.
    """

    
    # Créez l'image
    image = np.zeros((2 * size_factor, size_factor // 10, 4), dtype=np.uint8)
    image[:, :, 3] = 0  # Canal alpha à 0 pour une transparence complète
    
    # Vérifiez que l'image n'est pas vide
    if image is None or image.size == 0:
        raise ValueError("L'image est vide ou n'a pas été créée correctement")
    
    # Enregistrez l'image
    success = cv2.imwrite(dossier_images + "/" + nom, image)
    if not success:
        raise IOError("Erreur lors de l'enregistrement de l'image")

def inter_images_vide(nom, ratio):
    print(nom)
    """Crée une image vide en RGBA et l'enregistre sous le nom spécifié.

    Args:
        nom (str): Nom du fichier de sortie.
        size_factor (int): Facteur de taille pour l'image.

        ratio (float): ratio pour photobox. 

        
    """

    if ratio == 70.100 :
        ratio = 1.51

    
    # Créez l'image
    hauteur = ratio * size_factor
    largeur = size_factor // 10
    image = np.zeros((int(hauteur), largeur, 4), dtype=np.uint8)
    image[:, :, 3] = 0  # Canal alpha à 0 pour une transparence complète
    
    # Vérifiez que l'image n'est pas vide
    if image is None or image.size == 0:
        raise ValueError("L'image est vide ou n'a pas été créée correctement")
    
    # Enregistrez l'image
    success = cv2.imwrite(dossier_images + "/" + nom, image)
    if not success:
        raise IOError("Erreur lors de l'enregistrement de l'image")


def header(texte, fond):
    nom = "header.png"
    # Dimensions de l'image
    largeur = int(size_factor * 13.5*header_size)
    hauteur = int(size_factor * 1.3*header_size)


    # Couleurs
    couleur_fond = (0, 0, 0, 255)  # Noir avec transparence maximale (opaque)
    couleur_texte = (255, 255, 255, 255)  # Blanc avec transparence maximale (opaque)
    if not fond:
        couleur_fond = (255, 255, 255, 0)  # Blanc complètement transparent
        couleur_texte = (0, 0, 0, 255)  # Noir avec transparence maximale (opaque)
        texte = '-'.join(texte.split('-')[:-1])
        nom = "port_name.png"

    # Charger la police
    police = ImageFont.truetype(header_font, int(size_factor*header_size))  # Taille de la police
    image = Image.new('RGBA', (largeur, hauteur), couleur_fond)
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), texte, font=police)
    largeur_texte = bbox[2] - bbox[0]
    hauteur_texte = bbox[3] - bbox[1]
    position = ((largeur - largeur_texte) // 2, (hauteur - hauteur_texte) * 0.5 // 2)
    draw.text(position, texte, couleur_texte, font=police)
    image.save('processing_images/' + nom)
 
def stack_images(image1_path, image2_path, output_path):
    # Ouvrir les images avec Pillow
    image1 = Image.open(image1_path)
    image2 = Image.open(image2_path)

    # Vérifier que les images ont la même taille
    if image1.size != image2.size:
        raise ValueError("Les images n'ont pas la même taille.")

    # Créer une nouvelle image avec le même mode RGBA
    stacked_image = Image.new("RGBA", image1.size)

    # Combiner les deux images en les empilant
    stacked_image.paste(image1, (0, 0), image1)
    stacked_image.paste(image2, (0, 0), image2)

    # Enregistrer le résultat dans un nouveau fichier
    stacked_image.save(output_path)

def creee_image_fond(height, width, type=1):
    """Crée une image de fond avec une gradient de couleurs pastel

    Args:
        height (int): Hauteur de l'image de fond
        width (int): Largeur de l'image de fond
        type (int): Type de fond (  1 = zigzag vague, 
                                    2 = bleu flou bulles
                                    3 = bleu-gris plein
                                    4 = orange plein
                                    5 = kaki plein
                                    6 = bleu vif plein
                                    7 = bandes bleu orange kaki
                                    8 = rayé vif

    Returns:
        image (numpy.ndarray): Image de fond 
    """
    if type == 1:
    # Couleur de fond en type RGB
        background_color = (255, 255, 255)
        # Couleurs pastel en type RGB
        pastel_colors = [(100, 200, 200), (150, 200, 200), (120, 180, 180), (95, 200, 200), (170, 210, 210)]
        # Inverser l'ordre des composantes des couleurs pastel pour les convertir en type BGR
        for i in range(len(pastel_colors)):
            pastel_colors[i] = (pastel_colors[i][2], pastel_colors[i][1], pastel_colors[i][0])
        # Convertir les couleurs pastel en valeurs flottantes dans l'intervalle [0, 1]
        colors = [tuple(np.array(c) / 255.0) for c in pastel_colors]

        # Créer une image de fond blanche
        image = np.ones((height, width, 3), dtype=np.float32) * background_color

        nb_zigzags_per_line = height // (2*size_factor)
        zigzag_width = width // 9
        zigzag_height = height // nb_zigzags_per_line
        zigzag_thickness = height // (nb_zigzags_per_line)

        for i in range(nb_zigzags_per_line):
            # Coordonnées du premier point du zigzag
            y = i * zigzag_height
            color = colors[i % len(colors)]

            for x in range(0, width, zigzag_width):
                # Si le zigzag est impair
                if x % (2 * zigzag_width) == 0:
                    # Dessiner un zigzag dans le sens horaire
                    cv2.line(image, (x, y), (x + zigzag_width, y + zigzag_height), color, zigzag_thickness)
                # Si le zigzag est pair
                else:
                    # Dessiner un zigzag dans le sens anti-horaire
                    cv2.line(image, (x, y + zigzag_height), (x + zigzag_width, y), color, zigzag_thickness)

        # Convertir l'image en type np.uint8
        image = (image * 255).astype(np.uint8)

        cv2.imwrite("ressources/" + "colors.png", image)

    elif type == 2:
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)

        # Remplir l'image de cercles aléatoires
        for _ in range(1000):
            rayon = random.randint(width//20, width//10)
            x = random.randint(0, width)
            y = random.randint(0, height)
            couleur_bleu = random.randint(190, 255)  # Choix aléatoire de la composante bleue
            couleur = (110, 120, couleur_bleu)
            draw.ellipse([x - rayon, y - rayon, x + rayon, y + rayon], fill=couleur)
        image_blurred = image.filter(ImageFilter.GaussianBlur(radius=width//80))
        image_blurred.save("ressources/" + "colors.png")

    elif type == 3:
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[:] = (173, 162, 131)
        cv2.imwrite("ressources/" + 'colors.png', image)

    elif type == 4:
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[:] = (123, 176, 236)
        cv2.imwrite("ressources/" + 'colors.png', image)

    elif type == 5:
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[:] = (151, 171, 159)
        cv2.imwrite("ressources/" + 'colors.png', image)


    elif type == 6:
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[:] = (212, 196, 130)
        cv2.imwrite("ressources/" + 'colors.png', image)

    elif type == 7:
        ratio = 76.45  # pixels to size_factor ratio
        top_color = (173, 162, 131)
        middle_color = (123, 176, 236)
        bottom_color = (151, 171, 159)
        hauteur1 = int(height/2.71)
        hauteur2 =int(1.99*height/3)

        image = np.zeros((height, width, 3), dtype=np.uint8)

        image[:hauteur1] = top_color
        image[hauteur1:hauteur2] = middle_color
        image[hauteur2:] = bottom_color
        cv2.imwrite("ressources/" + 'colors.png', image)

    elif type == 8:
        ratio = 76.45  # pixels to size_factor ratio
        top_color = (167, 176, 118)       # Conversion de (118, 176, 167)
        middle_color = (142, 141, 241)    # Conversion de (241, 141, 142)
        bottom_color = (99, 164, 244)     # Conversion de (244, 164, 99)

        hauteur1 = int(height/2.567)
        hauteur2 =int(2.009*height/3)

        image = np.zeros((height, width, 3), dtype=np.uint8)

        image[:hauteur1] = top_color
        image[hauteur1:hauteur2] = middle_color
        image[hauteur2:] = bottom_color
        cv2.imwrite("ressources/" + 'colors.png', image)
    

def create_session_with_retry():
    """Crée une session requests avec retry configuré pour gérer les erreurs temporaires"""
    session = requests.Session()

    # Configuration des retries
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session










def recuperation_et_sauvegarde_url(url, port, m, year):
    """Récupère et sauvegarde les données de marées en utilisant le scrapper qui fonctionne

    Args:
        url (str): URL de base du site de marées
        port (str): Nom du port (ex: 'vieux-boucau-1052')
        m (str): Mois (ex: 'janvier' ou '01')
        year (str): Année (ex: '2026')

    Returns:
        str: Données de marées formatées ou None si échec
    """
    print(f"[SCRAPPER] recuperation_et_sauvegarde_url appelée avec port='{port}', m='{m}', year='{year}'")

    # Initialiser la base de données si nécessaire
    init_database()

    # Extraire le port_code depuis le nom du port (dernier élément après le dernier tiret)
    port_code = port.split('-')[-1]
    print(f"[SCRAPPER] Port code extrait: '{port_code}' depuis '{port}'")

    # Convertir le mois en numéro si nécessaire
    month_num = MONTH_MAPPING.get(m.lower(), m)
    print(f"[SCRAPPER] Mois converti: '{month_num}' depuis '{m}'")

    # Vérifier l'état des données dans la base de données
    print(f"[SCRAPPER] Vérification des données en base: port_code='{port_code}', month='{month_num}', year='{year}'")
    has_data, is_complete, days_count, expected_days = check_complete_month_data(port_code, month_num, year)

    if is_complete:
        print(f"[OK] Données complètes trouvées en base pour {port_code}-{month_num}-{year} ({days_count}/{expected_days} jours)")
        tide_data = get_tide_data_from_db(port_code, month_num, year)
        return tide_data
    elif has_data and not is_complete:
        print(f"[WARNING] Données partielles trouvées ({days_count}/{expected_days} jours), récupération des données manquantes...")
    else:
        print(f"[INFO] Aucune donnée trouvée en base pour {port_code}-{month_num}-{year}")
        print(f"[INFO] Tentative de récupération avec le scrapper...")

    # Vérifier que le scrapper est disponible
    if not SCRAPPER_AVAILABLE:
        print("[ERREUR] Scrapper non disponible - impossible de récupérer les données")
        return None

    # Convertir le mois en nom complet pour l'URL
    month_names = {
        '01': 'janvier', '02': 'fevrier', '03': 'mars', '04': 'avril',
        '05': 'mai', '06': 'juin', '07': 'juillet', '08': 'aout',
        '09': 'septembre', '10': 'octobre', '11': 'novembre', '12': 'decembre'
    }
    month_name = month_names.get(month_num, month_num)

    # Construire l'URL complète
    full_url = f"{url}/{port}/{month_name}-{year}"
    print(f"[SCRAPPER] URL construite: {full_url}")

    try:
        # Utiliser le scrapper pour récupérer les données
        scraped_data = scrape_tide_data(full_url)

        if scraped_data:
            print(f"[SCRAPPER] {len(scraped_data)} jours de données récupérés")

            # Convertir les données du scrapper en format texte pour la base de données
            tide_text = convert_scraper_data_to_text(scraped_data)

            if tide_text and len(tide_text.strip()) > 100:
                print(f"[SCRAPPER] Données converties ({len(tide_text)} caractères)")

                # Sauvegarder en base de données
                try:
                    # Créer le dossier TIDES si nécessaire
                    if not os.path.exists("TIDES"):
                        os.makedirs("TIDES")

                    # Sauvegarder dans le fichier
                    path_to_tide_file = f"TIDES/tides-{port}-{m}-{year}.txt"
                    with open(path_to_tide_file, "w", encoding="utf-8") as f:
                        f.write(tide_text)

                    # Sauvegarder aussi en base de données
                    save_tide_data_to_db(port_code, month_num, year, tide_text)
                    print(f"[OK] Données sauvegardées avec succès pour {port_code}-{month_num}-{year}")
                    return tide_text

                except Exception as e:
                    print(f"[ERREUR] Impossible de sauvegarder: {e}")
                    return tide_text  # Retourner quand même les données
            else:
                print("[ERREUR] Conversion des données échouée ou données insuffisantes")
                return None
        else:
            print("[ERREUR] Scrapper n'a pas réussi à récupérer les données")
            return None

    except Exception as e:
        print(f"[ERREUR] Erreur lors de l'utilisation du scrapper: {e}")
        import traceback
        traceback.print_exc()
        return None


def creation_image_complete(année, mois, port, taille, fonds, nom_sortie="image_fusionnee.png"):
    global year
    year = année
    global size_factor
    size_factor = taille

    # Initialiser la base de données et migrer les données existantes
    print("Initialisation de la base de données...")
    #init_database()

    #migrate_ports_to_db()
    #migrate_tides_to_db()

    cree_dossier_images()
    create_moon_image()
    url = "https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees"
    image_vide("0.png")
    header("CALENDRIER DES MARÉES "+year, True)
    header(port, False)
    image_vide("1.png")
    for m in mois :
        print(m+" "+year)
        draw(url, port, m, year,dossier_images+"/"+m+"-"+year+".png")
        inter_images_vide(str(m+"-"+year)+"toto.png", 70.1)

        


    image_vide("2.png")
    image_vide("3.png")

    stack_images_in_order(dossier_images, "out.png")

    img = cv2.imread("ressources/out.png")
    hauteur, largeur, c = img.shape

    print("generate background")
    for f in fonds :
        creee_image_fond(hauteur, largeur, int(f))
        print("combining images")
        
        # Charger les images RGBA et RGB
        image_rgba = cv2.imread("ressources/out.png", cv2.IMREAD_UNCHANGED)  # Assurez-vous que l'image RGBA est lue correctement (avec les 4 canaux)
        image_rgb = cv2.imread("ressources/" + 'colors.png')

        # Extraire les canaux RGBA
        rgba_channels = cv2.split(image_rgba)
        blue, green, red, alpha = rgba_channels

        # Convertir le canal alpha en un facteur de dilution (valeur entre 0 et 1)
        alpha_factor = alpha.astype(float) / 255.0

        # Mettre à jour les canaux RGB en utilisant le canal alpha comme facteur de dilution
        updated_red = (red * alpha_factor + image_rgb[:, :, 2] * (1 - alpha_factor)).astype(np.uint8)
        updated_green = (green * alpha_factor + image_rgb[:, :, 1] * (1 - alpha_factor)).astype(np.uint8)
        updated_blue = (blue * alpha_factor + image_rgb[:, :, 0] * (1 - alpha_factor)).astype(np.uint8)

        # Fusionner les canaux mis à jour en une seule image RGB
        merged_image = cv2.merge([updated_blue, updated_green, updated_red])


        output_folder = "OUTPUT IMAGES"
        os.makedirs(output_folder, exist_ok=True)
        cv2.imwrite(os.path.join(output_folder, nom_sortie[:-4]+"_"+str(f)+nom_sortie[-4:]), merged_image)
        
        print(nom_sortie, "  : FINITO")

def test_db_formatting():
    """Test rapide du formatage des données depuis la base de données"""
    print("=== TEST DU FORMATAGE DES DONNEES DEPUIS LA BASE ===\n")

    # Test avec vieux-boucau janvier 2026
    port_code = "1052"
    month = "01"
    year = "2026"

    print(f"Test de récupération depuis la base pour {port_code}-{month}-{year}")
    data = get_tide_data_from_db(port_code, month, year)

    if data:
        lines = data.split('\n')
        print(f"[OK] Donnees recuperees depuis la base: {len(lines)} lignes, {len(data)} caracteres")

        # Verifier le format des premieres lignes
        print("\nApercu du format:")
        for i, line in enumerate(lines[:15]):
            print(f"  {i+1:2d}: {line}")

        # Verification: compter les marees dans les premieres lignes
        maree_lines = [line for line in lines[:10] if line.startswith('Maree')]
        print(f"\nNombre de marees dans les 10 premieres lignes: {len(maree_lines)}")

        # Verifier que les marees sont dans le bon ordre chronologique
        if len(maree_lines) >= 2:
            print("Ordre chronologique des marees:")
            for i, line in enumerate(maree_lines[:4]):  # Montrer les 4 premieres marees
                print(f"  {i+1}. {line}")

        # Verifier la presence d'autres informations
        lune_line = next((line for line in lines[:10] if line.startswith('Lune')), None)
        if lune_line:
            print(f"Info lune trouvee: {lune_line}")

        saint_line = next((line for line in lines[:10] if line.startswith('Saint')), None)
        if saint_line:
            print(f"Info saint trouvee: {saint_line}")

    else:
        print("[ERREUR] Aucune donnee trouvee dans la base")

    print("\n=== FIN DU TEST ===")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_db_formatting()
    else:
        year = "2026"
        mois = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]
        port = "mimizan-1051"
        creation_image_complete(year, mois, port, 100, "7", port+"_"+year+".png")


