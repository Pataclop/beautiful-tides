#https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees/la-tranche-sur-mer-1080/mai-2024
import matplotlib.pyplot as plt
import numpy as np
import cv2

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
plt.savefig(temp_image_path, dpi=300, bbox_inches='tight')  # dpi contrôle la résolution de l'image

# Charger l'image temporaire avec OpenCV
image = cv2.imread(temp_image_path)

# Supprimer l'image temporaire
import os
os.remove(temp_image_path)

# Afficher l'image (optionnel)
cv2.imshow("Figure OpenCV", image)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Enregistrer l'image OpenCV dans un format spécifique (par exemple JPEG)
output_image_path = "output_plot.jpg"
cv2.imwrite(output_image_path, image)

