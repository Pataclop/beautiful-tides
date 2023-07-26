#https://gitlab.in2p3.fr/letg/extraction-ports-shom

import matplotlib.pyplot as plt

# Liste des hauteurs (exemples)
hauteurs = [4.89, 5.65, 5.78, 1.3]
heures = ["12:34", "12:55", "2:34", "23:55"]
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
    
# Tracer les points pour les hauteurs
ax.plot(abscisses, hauteurs)
ax.axis('off')

# Définir les limites des axes
#ax.set_xlim(0, len(hauteurs)*50)
#ax.set_ylim(0, max(hauteurs)*1.2)

# Afficher la grille
#ax.grid(True)

# Afficher le graphique
plt.show()
