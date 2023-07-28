import matplotlib.pyplot as plt
import numpy as np
import cv2
import requests
import csv
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from unidecode import unidecode
import re
import math
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os

NB_MAREE = 124



semaine = ["lu", "ma", "me", "je", "ve", "sa", "di"]

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
    all_spans = soup.find_all('span')
    # Créer un nouvel arbre HTML contenant uniquement les balises <span>
    new_soup = BeautifulSoup()
    new_html = new_soup.new_tag('html')
    new_soup.append(new_html)
    new_body = new_soup.new_tag('body')
    new_html.append(new_body)

    # Ajouter les balises <span> trouvées dans le nouvel arbre HTML
    all_spans = soup.find_all('span')

    # Obtenir les contenus des balises <span> dans une liste
    span_contents = [span.get_text() for span in all_spans]

    # Joindre les contenus par des virgules pour créer la chaîne finale
    cleaned_text = ', '.join(span_contents)

    return cleaned_text


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
    plt.plot(x_points, y_points, linestyle=linestyle)

def convert_to_minutes(heure_string):
    heures, minutes = heure_string.split('h')
    return int(heures) * 60 + int(minutes)

def convert_to_jours(jour_string):
    jour, nb = jour_string.split(' ')
    return int(nb)*1440


def get_image_creation_time(image_path):
    return os.path.getctime(image_path)


def stack_images_in_order(input_folder, output_filename):
    image_paths = sorted(Path(input_folder).glob("*.png"), key=get_image_creation_time)
    stacked_images = []

    for image_path in image_paths:
        image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)  # Include the alpha channel.
        stacked_images.append(image)

    max_width = max(image.shape[1] for image in stacked_images)
    total_height = sum(image.shape[0] for image in stacked_images)

    stacked_image = np.zeros((total_height, max_width, stacked_images[0].shape[2]), dtype=np.uint8)

    current_y = 0
    for image in stacked_images:
        h, w, _ = image.shape
        stacked_image[current_y:current_y + h, :w] = image
        current_y += h

    cv2.imwrite(output_filename, stacked_image)


def draw(link, nom):
    response = requests.get(link)
    if response.status_code != 200:
        print("Error: %s" % response.status_code)
        exit(1)
        
        
        
    soup = BeautifulSoup(response.content, "html.parser")
    t = clean(soup)
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
        
    lines = t.split('\n')
    tab = np.empty((NB_MAREE, 5), dtype=object)
    i = 0
    date = "rien 0"
    lune = None
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



    # Liste des hauteurs (exemples)
    hauteurs = np.zeros(NB_MAREE)
    for i in range(len(hauteurs)):
        if tab[i][2] is not None :
            hauteurs[i] = float(tab[i][2][:-1])

    hauteurs = np.delete(hauteurs, np.where(hauteurs == 0.0))
    moyenne_hauteur = np.mean(hauteurs)
    print (tab)
    heures = np.empty((NB_MAREE), dtype=object)
    for i in range(len(hauteurs)):
        if tab[i][1] is not None :
            heures[i] = tab[i][1]
    heures = np.delete(heures, np.where(heures == None))

    minutes = np.zeros(NB_MAREE)
    for i in range(len(heures)):
        minutes[i] = convert_to_minutes(heures[i])+convert_to_jours(tab[i][0])
    minutes = np.delete(minutes, np.where(minutes == 0))
    ecarts_successifs = np.diff(minutes)
    ecart_moyen = np.mean(ecarts_successifs)

    ESPACE_MAREE = ecart_moyen
    coeficient = np.empty((NB_MAREE), dtype=object)
    for i in range(len(coeficient)):
        if tab[i][3] is not None :
            coeficient[i] = (tab[i][3])

    # Créer une liste d'abscisses pour les hauteurs
    abscisses = [i*5 for i in range(len(hauteurs))]

    # Créer la figure et les axes
    fig, ax = plt.subplots()

    # Tracer les hauteurs sous forme de segments noirs
    for i in range(len(hauteurs) - 1):
        ax.plot([minutes[i], minutes[i+1]], [hauteurs[i], hauteurs[i+1]], color='black', linewidth=3)


    for x, y in zip(minutes, hauteurs):
        if y > moyenne_hauteur :
            ax.text(x, y+0.2, str(y)+"m", ha='center', va='bottom', fontname='Arial', fontsize=12, color='grey')
        else :
            ax.text(x, y-0.2, str(y)+"m", ha='center', va='top', fontname='Arial', fontsize=12, color='grey')
    tmp = 0
    ttmp = "t"
    ttmp2 = "r"
    angle = 0
    last =  0.0
    last2 = 0.0
    for x, y, h in zip(minutes, hauteurs, heures):
        if y > moyenne_hauteur :
            if tmp <= 1 :
                last = hauteurs[tmp+4]+1.45
            ax.text(x, y+0.52, h, ha='center', va='bottom', fontname='Arial', fontsize=12, color='black', weight='bold')
            jour = tab[tmp][0]
            if ttmp!= jour :
                pt1 = (x, hauteurs[tmp])
                pt2 = (0,0)
                if tmp+4<len(minutes):
                    pt2 = (minutes[tmp+4], hauteurs[tmp+4])
                else :
                    pt2 = (minutes[tmp], hauteurs[tmp])
                angle = calculer_angle_entre_points(pt1, pt2)
                ax.text((0.35+minutes[tmp]//1440)*1440, y+2.0, tab[tmp][0], rotation=angle*650, ha='center', va='center', color='black', fontsize=20)
                x_points = [minutes[tmp]//1440*1440, ((minutes[tmp]//1440)+1)*1440]
                if tmp+4<len(hauteurs):
                    y_points = [hauteurs[tmp]+1.45, hauteurs[tmp+4]+1.45]
                    if tmp>1:
                        y_points = [last, hauteurs[tmp+4]+1.45]
                        last = hauteurs[tmp+4]+1.45
                else :
                    y_points = [hauteurs[tmp]+1.45, hauteurs[tmp]+1.45]
                plot_line_with_dashes(x_points, y_points)
            ttmp = jour
        else :
            if tmp <= 1 :
                last2 = hauteurs[tmp+4]-1.45
            ax.text(x, y-0.8, h, ha='center', va='bottom', fontname='Arial', fontsize=12, color='black', weight='bold')
            jour = tab[tmp][0]
            if ttmp2!= jour :
                pt1 = (x, hauteurs[tmp])
                pt2 = (0,0)
                if tmp+4<len(minutes):
                    pt2 = (minutes[tmp+4], hauteurs[tmp+4])
                else :
                    pt2 = (minutes[tmp], hauteurs[tmp])
                angle = calculer_angle_entre_points(pt1, pt2)
                ax.text((0.35+minutes[tmp]//1440)*1440, y-1.9, tab[tmp][0], rotation=angle*650, ha='center', va='center', color='black', fontsize=20)
                x_points = [minutes[tmp]//1440*1440, ((minutes[tmp]//1440)+1)*1440]
                if x_points[1] == 0.0:
                    x_points[1] = x_points[0]
                if tmp+4<len(hauteurs):
                    y_points = [hauteurs[tmp]-1.45, hauteurs[tmp+4]-1.45]
                    if tmp>1:
                        y_points = [last2, hauteurs[tmp+4]-1.45]
                        last2 = hauteurs[tmp+4]-1.45
                else :
                    y_points = [hauteurs[tmp]-1.45, hauteurs[tmp]-1.45]
                plot_line_with_dashes(x_points, y_points)
            ttmp2 = jour
        tmp = tmp+1

    last_coef = 0
    for i in range(5):
        if coeficient[i] is not None and int(coeficient[i]) >10:
            last_coef = coeficient[i]   
    for x, y, c in zip(minutes, hauteurs, coeficient):
        if c is not None and int(c) > 10 :
            last_coef = c
        if y > moyenne_hauteur :
            if int(last_coef) > 95 :
                ax.text(x, moyenne_hauteur-0.3, str(last_coef), ha='center', va='bottom', fontname='Arial', fontsize=15, color='red', weight='bold')
            elif int(last_coef) < 35 :
                ax.text(x, moyenne_hauteur-0.3, str(last_coef), ha='center', va='bottom', fontname='Arial', fontsize=15, color='limegreen', weight='bold')
            else :
                ax.text(x, moyenne_hauteur-0.3, str(last_coef), ha='center', va='bottom', fontname='Arial', fontsize=14, color='black', weight='bold')

    plt.axis('off')
    largeur_pouces = 80
    hauteur_pouces = 6
    fig = plt.gcf()
    fig.set_size_inches(largeur_pouces, hauteur_pouces)
    plt.savefig(nom, transparent=True, dpi=300, bbox_inches='tight', format='png')


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


def create_gradient_image(width, height):
    # Créer une image vide avec des canaux B, G et R (valeurs 0)
    gradient_image = np.zeros((height, width, 3), dtype=np.uint8)

    # Créer un gradient vertical du jaune/vert au bleu marine
    for y in range(height):
        # Calculer la valeur de la couleur pour chaque ligne
        blue_value = int(255 * y / height)
        green_value = int(255 - (255 * y / height))

        # Remplir la ligne avec la couleur calculée
        gradient_image[y, :, 0] = blue_value  # Canal bleu
        gradient_image[y, :, 1] = green_value  # Canal vert
        gradient_image[y, :, 2] = 255  # Canal rouge (fixé à 255 pour avoir du jaune)

    return gradient_image




def image_mois(text):
    largeur = 18660
    hauteur = 1375
    # Créer une nouvelle image RGBA (mode "RGBA" pour gérer la transparence)
    image = Image.new("RGBA", (largeur, hauteur), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    x, y = 7930, 200
    police = ImageFont.truetype("AmaticSC-Bold.ttf", 700)
    couleur_texte = (0, 0, 0, 255)
    draw.text((x, y), text, font=police, fill=couleur_texte)
    image.save("IMAGES/"+text+".png")


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

dossier_images = "IMAGES"

if not os.path.exists(dossier_images):
    # Créer le dossier
    os.mkdir(dossier_images)

mois = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]
url = "https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees/le-verdon-sur-mer-1036/" 
mois = ["janvier", "fevrier"]


for m in mois :
    image_mois(m+" 2024")
    draw(url+m+"-2024","IMAGES/"+m+"-2024.png")









stack_images_in_order("IMAGES", "out.png")
