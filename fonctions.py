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
import backgrounds
Image.MAX_IMAGE_PIXELS = None

# Couche de donnees (base SQLite, parsing, recuperation) : re-exportee pour la
# retro-compatibilite (fonctions.DB_NAME, fonctions.MONTH_MAPPING,
# fonctions.recuperation_et_sauvegarde_url, fonctions.init_database, ...).
from db import *  # noqa: F401,F403

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

# Mapping des mois français vers leur numéro










#TODO essayer de rendre la taille de tout modifiable de facon harmonieuse via GUI. les espaces entre les machins et les tailles de police surtout.
# éventuellement les polices aussi. Et les seuils de marée rouge vert. 








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
    """Génère l'image de fond (ressources/colors.png) via le registre `backgrounds`.

    Le rendu des fonds 1-8 est identique au pixel près à l'ancienne implémentation
    (déplacée verbatim dans backgrounds.py) ; les fonds >= 9 sont de nouveaux styles.

    Args:
        height (int): Hauteur de l'image de fond
        width (int): Largeur de l'image de fond
        type (int|str): Identifiant du fond (voir backgrounds.FONDS)
    """
    backgrounds.generate_fond(
        str(type), height, width, size_factor,
        out_path=os.path.join(dossier_ressources, "colors.png"),
    )














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
    # `fonds` accepte une liste d'identifiants (recommandé, gère les ids >= 10)
    # ou une chaîne (legacy : itérée caractère par caractère).
    fond_ids = list(fonds) if isinstance(fonds, (list, tuple)) else list(str(fonds))
    for f in fond_ids :
        f = str(f)
        creee_image_fond(hauteur, largeur, f)
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


