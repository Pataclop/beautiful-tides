"""Couche de donnees de Beautiful Tides : base SQLite, parsing et recuperation.

Ce module ne depend PAS du moteur de rendu (matplotlib/cv2). Il peut donc etre
importe seul par l'interface et les scripts batch pour un demarrage leger et
fiable. Le code a ete extrait verbatim de l'ancien fonctions.py.
"""
import os
import re
import time
import sqlite3
import calendar
import traceback
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import du scrapper (optionnel : la lecture depuis la base reste possible sans lui)
try:
    from scrapper import scrape_tide_data
    SCRAPPER_AVAILABLE = True
except Exception:
    SCRAPPER_AVAILABLE = False
    scrape_tide_data = None
    print("[INFO] Scrapper non disponible - recuperation en direct desactivee")


# Configuration de la base de donnees

DB_NAME = "tides_database.db"


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

# Mois de l'annee dans l'ordre (noms francais utilises par le pipeline)
MONTHS_FR = ['janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin',
             'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre']


def future_months(year, months=None, reference=None):
    """Filtre les mois pour ne garder que ceux non passes de l'annee.

    Le scrapper ne doit interroger que les mois futurs (ou en cours) : les mois
    deja passes de l'annee courante sont exclus. Pour une annee future, tous les
    mois sont conserves ; pour une annee passee, aucun.

    Args:
        year (str|int): annee cible.
        months: sous-ensemble de MONTHS_FR (defaut : les 12 mois).
        reference (datetime): date de reference (defaut : maintenant).

    Returns:
        list[str]: mois a interroger, dans l'ordre.
    """
    from datetime import datetime
    if months is None:
        months = list(MONTHS_FR)
    ref = reference or datetime.now()
    y = int(year)
    if y > ref.year:
        return list(months)
    if y < ref.year:
        return []
    # Meme annee : garder le mois courant et les suivants.
    return [m for m in months if int(MONTH_MAPPING.get(m, '13')) >= ref.month]


def upcoming_months(reference=None, max_horizon=36):
    """Enumere les mois a venir, du mois courant vers le futur, sur plusieurs
    annees.

    Utilise pour « aspirer » tout ce que le site publie : on avance mois par
    mois jusqu'a atteindre l'horizon (au-dela, meteoconsult renvoie une 404).

    Args:
        reference (datetime): date de depart (defaut : maintenant).
        max_horizon (int): nombre maximum de mois a enumerer (garde-fou).

    Returns:
        list[tuple[str, str]]: [(annee, nom_du_mois), ...] dans l'ordre chrono.
    """
    from datetime import datetime
    ref = reference or datetime.now()
    out = []
    for k in range(max_horizon):
        idx = (ref.month - 1) + k
        year = ref.year + idx // 12
        month_name = MONTHS_FR[idx % 12]
        out.append((str(year), month_name))
    return out


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
