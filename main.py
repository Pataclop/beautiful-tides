import matplotlib.pyplot as plt
import numpy as np
import cv2
import requests
import csv
from bs4 import BeautifulSoup
from unidecode import unidecode
import re




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

def clean (soupe) :
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

url = "https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees/le-verdon-sur-mer-1036/aout-2023"  # Remplacez cela par l'URL de la page que vous souhaitez scraper

response = requests.get(url)
if response.status_code == 200:
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
    ecrire_texte_dans_csv(t, "out.txt ")











# Liste des hauteurs (exemples)
hauteurs = [4.89, 2.10, 4.99, 2.05, 4.89, 2.10, 4.99, 2.05]
heures = ["12:34", "12:55", "2:34", "23:55","12:34", "12:55", "2:34", "23:55"]
coeficient = ["90", "92", "94", "93","90", "92", "94", "93"]

# Créer une liste d'abscisses pour les hauteurs
abscisses = [i*50 for i in range(len(hauteurs))]

# Créer la figure et les axes
fig, ax = plt.subplots()

# Tracer les hauteurs sous forme de segments noirs
for i in range(len(hauteurs) - 1):
    ax.plot([abscisses[i], abscisses[i+1]], [hauteurs[i], hauteurs[i+1]], color='black')


for x, y in zip(abscisses, hauteurs):
    ax.text(x, y+0.2, f'{y}', ha='center', va='bottom', fontname='Arial', fontsize=12, color='blue', weight='bold')
    
for x, y, h in zip(abscisses, hauteurs, heures):
    ax.text(x, y+0.4, h, ha='center', va='bottom', fontname='Arial', fontsize=12, color='blue', weight='bold')

for x, y, i in  zip(abscisses, hauteurs, coeficient):
    ax.text(x, 3.5, i, ha='center', va='bottom', fontname='Arial', fontsize=12, color='blue', weight='bold')
# Tracer les points pour les hauteurs
ax.plot(abscisses, hauteurs)
ax.axis('off')

#plt.show()

temp_image_path = "temp_plot.png"
plt.savefig(temp_image_path, dpi=100, bbox_inches='tight')  # dpi contrôle la résolution de l'image

# Charger l'image temporaire avec OpenCV
image = cv2.imread(temp_image_path)

# Supprimer l'image temporaire
import os
os.remove(temp_image_path)

# Afficher l'image (optionnel)
#cv2.imshow("Figure OpenCV", image)
#cv2.waitKey(0)
cv2.destroyAllWindows()

# Enregistrer l'image OpenCV dans un format spécifique (par exemple JPEG)
output_image_path = "output_plot.jpg"
cv2.imwrite(output_image_path, image)

