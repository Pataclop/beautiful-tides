#!/usr/bin/env python3
"""
Scrapper pour récupérer les données de marées depuis marine.meteoconsult.fr
Exporte les données en format CSV avec toutes les informations utiles.
"""

import sys
import csv
import re
import time
import random
from datetime import datetime
from urllib.parse import urlparse, parse_qs

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("ERREUR: Playwright n'est pas installé. Installez-le avec: pip install playwright")
    print("Puis exécutez: playwright install")
    sys.exit(1)

from bs4 import BeautifulSoup

def setup_browser():
    """Configure le navigateur pour ressembler à un vrai Chrome"""
    return {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'viewport': {'width': 1366, 'height': 768},
        'locale': 'fr-FR',
        'timezone_id': 'Europe/Paris',
        'geolocation': {'longitude': 2.3522, 'latitude': 48.8566},  # Paris coordinates
        'permissions': ['geolocation'],
        'extra_http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Referer': 'https://www.google.fr/'
        }
    }

def extract_tide_data_from_page(page_content, url):
    """
    Extrait les données de marées depuis le contenu HTML de la page
    Utilise la structure spécifique du site marine.meteoconsult.fr
    """
    soup = BeautifulSoup(page_content, 'html.parser')
    tide_data = []

    # Extraire le nom du port depuis l'URL
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split('/')
    port_info = ""
    for part in path_parts:
        if '-' in part and any(char.isdigit() for char in part):
            port_info = part
            break

    # Extraire l'année et le mois depuis l'URL pour construire les dates complètes
    url_parts = parsed_url.path.split('/')
    year_month = ""
    for part in url_parts:
        if any(month in part.lower() for month in ['janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin',
                                                   'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre']):
            year_month = part  # ex: "decembre-2025"
            break

    if year_month:
        month_name, year = year_month.split('-')
        month_mapping = {
            'janvier': '01', 'fevrier': '02', 'mars': '03', 'avril': '04',
            'mai': '05', 'juin': '06', 'juillet': '07', 'aout': '08',
            'septembre': '09', 'octobre': '10', 'novembre': '11', 'decembre': '12'
        }
        month_num = month_mapping.get(month_name.lower(), '01')
    else:
        year = "2025"
        month_num = "12"

    # Trouver tous les jours (basés sur les éléments tide-date)
    day_elements = soup.find_all('div', class_='tide-date')

    for day_elem in day_elements:
        date_text = day_elem.get_text(strip=True)
        # Extraire le numéro du jour depuis "lundi 1", "mardi 2", etc.
        day_match = re.search(r'(\d{1,2})$', date_text)
        if not day_match:
            continue

        day = day_match.group(1)
        full_date = f"{year}-{month_num}-{int(day):02d}"

        # Trouver le conteneur de marées pour ce jour
        container = day_elem.find_next('div', class_='tide-container')
        if not container:
            continue

        # Trouver la phase lunaire pour ce jour (dans la section ephemeris qui suit)
        lunar_phase = ""
        ephemeris = container.find_next('div', class_='ephemeris')
        if ephemeris:
            state_elem = ephemeris.find('span', class_='state')
            if state_elem:
                lunar_phase = state_elem.get_text(strip=True)

        # Initialiser les données du jour
        day_data = {
            'date': full_date,
            'port': port_info,
            'marees': []
        }

        # Traiter chaque ligne de marées (tide-line)
        tide_lines = container.find_all('div', class_='tide-line')

        for tide_line in tide_lines:
            # Trouver le coefficient pour cette ligne
            coef_elem = tide_line.find('div', class_=re.compile(r'coef tide-coef-level-\d+'))
            coefficient = ""
            if coef_elem:
                coef_text = coef_elem.get_text(strip=True)
                if coef_text.isdigit():
                    coefficient = coef_text

            # Chercher les marées hautes et basses dans cette ligne
            high_tides = tide_line.find_all('div', class_='high-tide')
            low_tides = tide_line.find_all('div', class_='low-tide')

            # Traiter les marées hautes
            for high_tide in high_tides:
                hour_elem = high_tide.find('span', class_='hour')
                height_elem = high_tide.find('span', class_='height')

                if hour_elem and height_elem:
                    hour = hour_elem.get_text(strip=True)
                    height = height_elem.get_text(strip=True)

                    # Normaliser l'heure (01h26 -> 01:26)
                    hour = re.sub(r'h', ':', hour)

                    day_data['marees'].append({
                        'heure': hour,
                        'type': 'haute',
                        'hauteur': height,
                        'coefficient': coefficient
                    })

            # Traiter les marées basses
            for low_tide in low_tides:
                hour_elem = low_tide.find('span', class_='hour')
                height_elem = low_tide.find('span', class_='height')

                if hour_elem and height_elem:
                    hour = hour_elem.get_text(strip=True)
                    height = height_elem.get_text(strip=True)

                    # Normaliser l'heure (07h10 -> 07:10)
                    hour = re.sub(r'h', ':', hour)

                    day_data['marees'].append({
                        'heure': hour,
                        'type': 'basse',
                        'hauteur': height,
                        'coefficient': coefficient
                    })

        # Ajouter la phase lunaire à toutes les marées du jour
        if lunar_phase:
            for maree in day_data['marees']:
                maree['phase_lunaire'] = lunar_phase

        # Ajouter les données du jour seulement s'il y a des marées
        if day_data['marees']:
            tide_data.append(day_data)

    # Les phases lunaires sont déjà extraites pour chaque jour dans la boucle principale

    return tide_data

def scrape_tide_data(url):
    """
    Récupère les données de marées depuis l'URL donnée
    """
    print(f"[MAREES] Scraping des donnees de marees depuis: {url}")
    print("[INIT] Initialisation du navigateur anti-detection...")

    browser_config = setup_browser()

    try:
        with sync_playwright() as p:
            # Lancer le navigateur pour ressembler à un vrai Chrome
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-default-apps',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
                ]
            )

            context = browser.new_context(
                user_agent=browser_config['user_agent'],
                viewport=browser_config['viewport'],
                locale=browser_config['locale'],
                timezone_id=browser_config['timezone_id'],
                geolocation=browser_config['geolocation'],
                permissions=browser_config['permissions'],
                extra_http_headers=browser_config['extra_http_headers']
            )

            # Ajouter des cookies pour paraître plus légitime
            context.add_cookies([
                {
                    'name': 'lang',
                    'value': 'fr',
                    'domain': 'marine.meteoconsult.fr',
                    'path': '/'
                },
                {
                    'name': 'timezone',
                    'value': 'Europe/Paris',
                    'domain': 'marine.meteoconsult.fr',
                    'path': '/'
                }
            ])

            page = context.new_page()

            # Masquer le fait que c'est un navigateur automatisé
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                window.navigator.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
            """)

            # Configurer des délais aléatoires pour paraître plus humain
            page.route("**/*", lambda route: route.continue_())

            print("[NAVIGATION] Navigation vers la page...")
            response = page.goto(url, wait_until='networkidle', timeout=60000)

            if not response.ok:
                print(f"[ERREUR] Erreur HTTP: {response.status}")
                # Essayer avec referer
                print("[RETRY] Tentative avec referer...")
                page.set_extra_http_headers({'Referer': 'https://www.google.fr/'})
                response = page.goto(url, wait_until='networkidle', timeout=60000)
                if not response.ok:
                    return None

            print("[ATTENTE] Attente du rendu JavaScript complet...")

            # Simuler un comportement humain
            page.wait_for_timeout(random.randint(100, 400))

            # Mouvement de souris aléatoire
            page.mouse.move(random.randint(100, 400), random.randint(100, 400))
            page.wait_for_timeout(random.randint(300, 400))

            # Scroll léger pour simuler lecture
            page.evaluate("window.scrollTo(0, " + str(random.randint(100, 400)) + ")")
            page.wait_for_timeout(random.randint(100, 400))

            # Attente finale
            page.wait_for_timeout(random.randint(100, 500))

            # Récupérer le contenu HTML rendu
            content = page.content()
            print(f"[CONTENU] Contenu recupere: {len(content)} caracteres")

            # Sauvegarder le contenu pour debug
            #debug_filename = f"debug_scraped_content_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            #with open(debug_filename, 'w', encoding='utf-8') as f:
            #    f.write(content)
            #print(f"[DEBUG] Contenu sauvegarde dans: {debug_filename}")

            # Extraire les données de marées
            tide_data = extract_tide_data_from_page(content, url)

            browser.close()

            if tide_data:
                print(f"[SUCCES] {len(tide_data)} jours de donnees de marees extraits")
                return tide_data
            else:
                print("[ATTENTION] Aucune donnee de maree trouvee")
                return None

    except Exception as e:
        print(f"[ERREUR] Erreur lors du scraping: {e}")
        return None

def flatten_tide_data(tide_data):
    """
    Aplatit les données de marées pour l'export CSV
    Chaque marée devient une ligne séparée avec son coefficient et phase lunaire spécifiques
    """
    flattened_data = []

    for day_data in tide_data:
        base_info = {
            'date': day_data.get('date', ''),
            'port': day_data.get('port', '')
        }

        marees = day_data.get('marees', [])
        if marees:
            for maree in marees:
                row = base_info.copy()
                row.update({
                    'heure_maree': maree.get('heure', ''),
                    'type_maree': maree.get('type', ''),
                    'hauteur_maree': maree.get('hauteur', ''),
                    'coefficient': maree.get('coefficient', ''),
                    'phase_lunaire': maree.get('phase_lunaire', '')
                })
                flattened_data.append(row)

    return flattened_data

def export_to_csv(tide_data, filename="marees_export.csv"):
    """
    Exporte les données de marées vers un fichier CSV
    """
    if not tide_data:
        print("[ERREUR] Aucune donnee a exporter")
        return False

    flattened_data = flatten_tide_data(tide_data)

    if not flattened_data:
        print("[ERREUR] Aucune donnee apres aplatissement")
        return False

    # Définir les colonnes du CSV
    fieldnames = [
        'date', 'port', 'heure_maree', 'type_maree', 'hauteur_maree',
        'coefficient', 'phase_lunaire'
    ]

    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in flattened_data:
                writer.writerow(row)

        print(f"[EXPORT] Donnees exportees vers {filename} ({len(flattened_data)} lignes)")
        return True

    except Exception as e:
        print(f"[ERREUR] Erreur lors de l'export CSV: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python scrapper.py <URL>")
        print("Exemple: python scrapper.py 'https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees/pointe-de-grave-59/decembre-2025#26-12'")
        sys.exit(1)

    url = sys.argv[1].strip()

    # Validation basique de l'URL
    if not url.startswith('http'):
        print("[ERREUR] L'URL doit commencer par http:// ou https://")
        sys.exit(1)

    print("=" * 60)
    print("=== SCRAPPER DE DONNEES DE MAREES ===")
    print("=" * 60)

    # Récupérer les données
    tide_data = scrape_tide_data(url)

    if tide_data:
        # Générer le nom du fichier basé sur l'URL et la date
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parsed_url = urlparse(url)
        port_name = ""
        for part in parsed_url.path.split('/'):
            if '-' in part and any(char.isdigit() for char in part):
                port_name = part.replace('-', '_')
                break

        filename = f"marees_{port_name}_{timestamp}.csv" if port_name else f"marees_{timestamp}.csv"

        # Exporter en CSV
        success = export_to_csv(tide_data, filename)

        if success:
            print("\n" + "=" * 60)
            print("[SUCCES] SCRAPING TERMINE AVEC SUCCES")
            print(f"[FICHIER] Fichier genere: {filename}")
            print("=" * 60)
        else:
            print("[ERREUR] Echec de l'export")
            sys.exit(1)
    else:
        print("[ERREUR] Echec du scraping")
        sys.exit(1)

if __name__ == "__main__":
    main()
