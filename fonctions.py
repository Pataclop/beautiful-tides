import matplotlib.pyplot as plt
import numpy as np
import cv2
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from unidecode import unidecode
import re
import math
import random
from matplotlib.font_manager import FontProperties
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import shutil

font_path = 'fonts/FUTURANEXTDEMIBOLDITALIC.TTF'  # Assurez-vous que le chemin est correct
font_path2 = 'fonts/FUTURANEXTLIGHT.TTF'
font_hauteur = FontProperties(fname=font_path2)
jours_font = FontProperties(fname=font_path)
NB_MAREE = 124
fancy_font = "fonts/AmaticSC-Bold.ttf"
regular_font = "Arial"
minutes_dans_journée = 1440
semaine = ["lu", "ma", "me", "je", "ve", "sa", "di"]
dossier_images = "IMAGES"
size_factor = 300
marge_pointillets = 50
hauteur_jour = 1.8
epaisseur_trait_jour = 1.0
limite_haut_coef = 95
limite_bas_coef = 35

#TODO essayer de rendre la taille de tout modifiable de facon harmonieuse via GUI. les espaces entre les machins et les tailles de police surtout.
# éventuellement les polices aussi. Et les seuils de marée rouge vert. 

# raise error if sizefactor is less than 12
if size_factor < 10:
    raise ValueError("size factor must be >10")


def cree_dossier_images():
    if os.path.exists(dossier_images):
        shutil.rmtree(dossier_images)
    os.mkdir(dossier_images)

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

def recuperation_et_nettoyage_page_web(url):
    response = requests.get(url)
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

def draw(link, nom):
    lines = recuperation_et_nettoyage_page_web(link).split('\n')
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

    # Tracer les hauteurs sous forme de segments noirs inclinés
    ax.plot(minutes, hauteurs, color='black', linewidth=6)



    for x, y in zip(minutes, hauteurs):
        if y > moyenne_hauteur :
            ax.text(x, y+0.2, str(y)+"m", ha='center', va='bottom', fontproperties=font_hauteur, fontsize=15, color='black')
        else :
            ax.text(x, y-0.2, str(y)+"m", ha='center', va='top', fontproperties=font_hauteur, fontsize=15, color='black')
    line_index = 0
    current_day = "t"
    previous_day = "r"
    angle = 0
    hauteur_précédente =  0.0
    hauteur_précédente_2 = 0.0
    #TODO il y a un bug occasionnel, je ne sais pas pourquoi, mais pour les pointillets en trait, pour le dernier jour (peut etre pour le premier aussi), 
    #pour le dernier segment complet, le début du segment ne va âs etre raccord avec celui du jour précédent. il y a une marche. il doit y avoir un bug de hauteur précédente ou hauteur précedente 2
    décalage_hauteur_petits_traits = 1.45

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
        if line_index <= 1:
            hauteur_to_update = operation(hauteurs[line_index+4], décalage_hauteur_petits_traits, updown)
        ax.text(x, operation(y, 0.6 if updown == 1 else 1.0, updown), h, ha='center', va='bottom', fontproperties=font_hauteur, fontsize=15, color='black', weight='bold')
        jour = tab[line_index][0]
        if day != jour:
            pt1 = (x, hauteurs[line_index])
            pt2 = (0,0)
            if line_index+4<len(minutes):
                pt2 = (minutes[line_index+4], hauteurs[line_index+4])
            else:
                pt2 = (minutes[line_index], hauteurs[line_index])
            angle = calculer_angle_entre_points(pt1, pt2)
            jour_to_write, date_to_write =  tab[line_index][0].split(" ")
            nom_jour = jour_to_write[0].upper()+date_to_write
            ax.text((0.28+minutes[line_index]//minutes_dans_journée)*minutes_dans_journée, operation(y, hauteur_jour if updown == 1 else hauteur_jour, updown), nom_jour, fontproperties=jours_font, rotation=angle*650, ha='center', va='center', color='black', fontsize=23)
            x_points = [minutes[line_index]//minutes_dans_journée*minutes_dans_journée, ((minutes[line_index]//minutes_dans_journée)+1)*minutes_dans_journée]
            if updown<0:
                if x_points[1] == 0.0:
                    x_points[1] = x_points[0]
            if line_index+4<len(hauteurs):
                y_points = [operation(hauteurs[line_index],décalage_hauteur_petits_traits, updown), operation(hauteurs[line_index+4], décalage_hauteur_petits_traits, updown)]
                if line_index>1:
                    y_points = [hauteur_to_update, operation(hauteurs[line_index+4],décalage_hauteur_petits_traits, updown)]
                    hauteur_to_update = operation(hauteurs[line_index+4],décalage_hauteur_petits_traits, updown)
            else:
                y_points = [operation(hauteurs[line_index],décalage_hauteur_petits_traits, updown), operation(hauteurs[line_index],décalage_hauteur_petits_traits, updown)]
            plot_line_with_dashes(x_points, y_points)
        return jour, hauteur_to_update


    for x, y, h in zip(minutes, hauteurs, heures):


        if y > moyenne_hauteur :
            current_day, hauteur_précédente = draw_stuff(hauteur_précédente, 1, current_day)
        else :
            previous_day, hauteur_précédente_2 = draw_stuff(hauteur_précédente_2, -1, previous_day)
        line_index = line_index+1


    last_coef = 0
    for i in range(5):
        if coeficient[i] is not None and int(coeficient[i]) >10:
            last_coef = coeficient[i]   
    
    def couleur_coefficient(couleur):
        ax.text(x, moyenne_hauteur-0.5, str(last_coef), ha='center', va='bottom', fontname=regular_font, fontsize=18, color=couleur, weight='bold')
    for x, y, c in zip(minutes, hauteurs, coeficient):
        if c is not None and int(c) > 10 :
            last_coef = c
        if y > moyenne_hauteur :
            if int(last_coef) > limite_haut_coef :
                couleur_coefficient('red')
            elif int(last_coef) < limite_bas_coef :
                couleur_coefficient('forestgreen')
            else :
                couleur_coefficient('black')

    plt.axis('off')
    largeur_pouces = 80
    hauteur_pouces = 6
    fig = plt.gcf()
    fig.set_size_inches(largeur_pouces, hauteur_pouces)
    plt.savefig(nom, transparent=True, dpi=size_factor, bbox_inches='tight', format='png')

    #ici on élargit l'image (on rajoute une zone a gauche) pour avoir la place plus tard d'écrire le mois
    image = cv2.imread(nom, cv2.IMREAD_UNCHANGED)
    height, width, _ = image.shape
    padded_image = np.zeros((height, (width+int(0.75*height)), 4), dtype=np.uint8)
    # Copier l'image d'entrée à droite avec un espace vide à gauche
    padded_image[:, int(0.75*height):] = image
    cv2.imwrite(nom, padded_image)
    #et on écrit le mois
    write_text_on_image(nom, nom[7:-9], 30, (size_factor, size_factor//3), fancy_font, int(size_factor*1.25))

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
    """Crée une image vide en RGBA et l'enregistre sous le nom spécifié. utile pour espacer les images des bords haut et bas de l'image finale lors de l'assemblage
    image pas large, p as besoin. image haute. le canal alpha est initialisé à 0 pour une transparence complète.

    Args:
        nom (str): Nom du fichier de sortie.
    """
    image = np.zeros((2*size_factor, size_factor//10, 4), dtype=np.uint8)
    image[:, :, 3] = 0  # Canal alpha à 0 pour une transparence complète
    cv2.imwrite("IMAGES/"+nom, image)

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
        type (int): Type de fond (1 = zigzag vague, 2 = bleu flou bulles)

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

        cv2.imwrite("colors.png", image)

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
        image_blurred.save("colors.png")

def creation_image_complete(mois, port, taille, fond, nom_sortie="image_fusionnee.png"):
    cree_dossier_images()
    global size_factor
    size_factor = taille

    url = "https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees/" + port + "/" 

    image_vide("1.png")
    for m in mois :
        print(m+" 2024")
        draw(url+m+"-2024","IMAGES/"+m+"-2024.png")

    #image_vide("2.png")
    image_vide("3.png")
    image_vide("4.png")

    stack_images_in_order("IMAGES", "out.png")

    img = cv2.imread("out.png")
    hauteur, largeur, c = img.shape

    creee_image_fond(hauteur, largeur, fond)

    # Charger les images RGBA et RGB
    image_rgba = cv2.imread('out.png', cv2.IMREAD_UNCHANGED)  # Assurez-vous que l'image RGBA est lue correctement (avec les 4 canaux)
    image_rgb = cv2.imread('colors.png')

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


    cv2.imwrite(nom_sortie, merged_image)
    
    print("FINITO")

#TODO créer une image en tete avec l'année et le nom du port et peut etre d'autres choses je sais pas quoi
#TODO ca serait bien d'avoir la lune aussi. 
if __name__ == "__main__":
    mois = ["juin"]
    port = "saint-jean-de-luz-61"
    creation_image_complete(mois, port, 100, 1)

