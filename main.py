import matplotlib.pyplot as plt
import numpy as np
import cv2
import requests
import csv
from bs4 import BeautifulSoup
from unidecode import unidecode
import re


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
    tab = np.empty((124, 5), dtype=object)
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
    hauteurs = np.zeros(124)
    for i in range(len(hauteurs)):
        if tab[i][2] is not None :
            hauteurs[i] = float(tab[i][2][:-1])

    hauteurs = np.delete(hauteurs, np.where(hauteurs == 0.0))
    moyenne_hauteur = np.mean(hauteurs)
    print (tab)
    heures = np.empty((124), dtype=object)
    for i in range(len(hauteurs)):
        if tab[i][1] is not None :
            heures[i] = tab[i][1]
    heures = np.delete(heures, np.where(heures == ""))

    coeficient = np.empty((124), dtype=object)
    for i in range(len(coeficient)):
        if tab[i][3] is not None :
            coeficient[i] = (tab[i][3])

    # Créer une liste d'abscisses pour les hauteurs
    abscisses = [i*5 for i in range(len(hauteurs))]

    # Créer la figure et les axes
    fig, ax = plt.subplots()

    # Tracer les hauteurs sous forme de segments noirs
    for i in range(len(hauteurs) - 1):
        ax.plot([abscisses[i], abscisses[i+1]], [hauteurs[i], hauteurs[i+1]], color='black', linewidth=3)


    for x, y in zip(abscisses, hauteurs):
        if y > moyenne_hauteur :
            ax.text(x, y+0.2, f'{y}', ha='center', va='bottom', fontname='Arial', fontsize=12, color='grey', weight='bold')
        else :
            ax.text(x, y-0.2, f'{y}', ha='center', va='top', fontname='Arial', fontsize=12, color='grey', weight='bold')
    tmp = 0
    ttmp = "t"
    for x, y, h in zip(abscisses, hauteurs, heures):
        if y > moyenne_hauteur :
            ax.text(x, y+0.4, h, ha='center', va='bottom', fontname='Arial', fontsize=12, color='black', weight='bold')
            jour = tab[tmp][0]
            if ttmp!= jour :
                ax.text(x, y+1.2, tab[tmp][0], rotation=3, ha='center', va='center', color='black', fontsize=20)
            ttmp = jour
        else :
            ax.text(x, y-0.6, h, ha='center', va='bottom', fontname='Arial', fontsize=12, color='black', weight='bold')
        tmp = tmp+1

    last_coef = 0
    for i in range(5):
        if coeficient[i] is not None and int(coeficient[i]) >10:
            last_coef = coeficient[i]   
    for x, y, c in zip(abscisses, hauteurs, coeficient):
        if c is not None and int(c) > 10 :
            last_coef = c
        if y > moyenne_hauteur :
            if int(last_coef) > 95 :
                ax.text(x, moyenne_hauteur-0.3, str(last_coef), backgroundcolor=(1.0, 0.9, 0.0, 0.5), ha='center', va='bottom', fontname='Arial', fontsize=14, color='black', weight='bold')
            else :
                ax.text(x, moyenne_hauteur-0.3, str(last_coef), ha='center', va='bottom', fontname='Arial', fontsize=14, color='black', weight='bold')

    plt.axis('off')
    largeur_pouces = 80
    hauteur_pouces = 6
    fig = plt.gcf()
    fig.set_size_inches(largeur_pouces, hauteur_pouces)
    plt.savefig(nom, dpi=300, bbox_inches='tight')
    
mois = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]
url = "https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees/le-verdon-sur-mer-1036/" 
mois = ["aout"]
for m in mois :
    draw(url+m+"-2023", m+"-2023.png")