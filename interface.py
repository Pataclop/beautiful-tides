import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel, QScrollArea, QAbstractItemView
from PyQt5.QtGui import QPixmap, QWheelEvent, QColor
from PyQt5.QtCore import Qt
from urllib.request import urlopen
import requests
import fonctions
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Choix Parametres")
        self.setGeometry(50, 50, 1700, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QHBoxLayout(self.central_widget)

        self.year_selector = QListWidget()
        self.year_selector.setFixedWidth(50)
        self.year_selector.addItems(["2024", "2025", "2026"]) # Ajoutez d'autres années si nécessaire
        self.year_selector.itemSelectionChanged.connect(self.on_month_selection_changed)

    #TODO il faudrait un truc pour savoir dans quel ordre se servir des trucs. 1 - port   2- année   3- mois   4- créer

        self.month_list = QListWidget()
        self.month_list.setFixedWidth(100)
        self.month_list.addItems(["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"])
        self.month_list.setSelectionMode(QAbstractItemView.MultiSelection)

        self.port_selector = QListWidget()
        self.port_selector.setFixedWidth(150)
        #il faudrait un truc pour afficher le nom joli mais renvoyer le nom moche complet
        self.port_selector.addItems(["brest-4", "dunkerque-7", "paimpol-957", "loctudy-987", "lorient-57", "pornic-1020", "ile-d-yeu-port-joinville-1023", "la-rochelle-ville-1027", "ile-de-re-saint-martin-1026", "saint-denis-d-oleron-1067", "le-verdon-sur-mer-1036", "cap-ferret-1045", "vieux-boucau-1052", "saint-jean-de-luz-61"])

        self.scroll_area = QScrollArea()
        self.scroll_area.setFixedWidth(1300)
        self.scroll_area.setFixedHeight(600)
        self.scroll_area.setWidgetResizable(True)

        self.image_label = QLabel()
        self.scroll_area.setWidget(self.image_label)

        self.preview_button = QPushButton("preview")
        self.preview_button.clicked.connect(self.preview)



        self.print_button = QPushButton("Créer avec les mois sélectionnés")
        self.print_button.clicked.connect(self.print_selected_months)

        self.layout.addWidget(self.port_selector)
        self.layout.addWidget(self.year_selector)
        self.layout.addWidget(self.month_list)
        

#TODO il faut parametres pour personaliser un peu l'affichage. des optiopns (lune, saint, jsp), la police et la taile des éléments. 
#que tout soit personalisable. les couleurs aussi éventuellement. c'est une grosse interface mais c'estr bien quand meme. 

        self.image_layout = QVBoxLayout()
        self.image_layout.addWidget(self.scroll_area)
        self.image_layout.addWidget(self.preview_button)
        self.image_layout.addWidget(self.print_button)

        self.layout.addLayout(self.image_layout)
    
#TODO y'a des bugs ca se superpose je sais pas pouruqoi c'est bizarre, du a l'interface ? jsp. il est tard.
    def preview(self):
        selected_months = [[self.month_list.item(i).text() for i in range(self.month_list.count()) if self.month_list.item(i).isSelected()][0]]
        selected_port = self.port_selector.currentItem().text()

        print(f"Mois sélectionnés : {selected_months}")
        print(f"Port : {selected_port}")
        fonctions.creation_image_complete(selected_months, selected_port, 60, 1)
        self.refresh_image()

    def print_selected_months(self):
        #TODO il faut aussi envoyer l'année.
        selected_months = [self.month_list.item(i).text() for i in range(self.month_list.count()) if self.month_list.item(i).isSelected()]
        selected_port = self.port_selector.currentItem().text()
        fonctions.creation_image_complete(selected_months, selected_port, 200, 1)

    def on_month_selection_changed(self):
        #change mouse cursor to waiting cursor and change the color of the cursor
        QApplication.setOverrideCursor(Qt.WaitCursor)

        selected_months = [self.month_list.item(i).text() for i in range(self.month_list.count()) if self.month_list.item(i).isSelected()]
        print(f"Mois sélectionnés : {selected_months}")

        for i in range(self.month_list.count()):
            item = self.month_list.item(i)
            item_name = self.month_list.item(i).text()
            year = self.year_selector.currentItem().text()
            port = self.port_selector.currentItem().text()
            url = f"https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees/{port}/{item_name}-{year}"
            print (url)
            try:
                response = requests.head(url)
                #TODO améliorer la vérification des pages web existantes ou non. là ca marche pas pour les années suivantes puisque la page existe souvent mais n'est pas remplie. il faudrait tester si la page est remplie.
                if response.status_code == 200:
                    print("ok")
                    item.setForeground(QColor("green"))
                else:
                    print("not ok")
                    item.setForeground(QColor("red"))
            except:
                print("error")
                item.setForeground(QColor("red"))

        QApplication.restoreOverrideCursor()

    def refresh_image(self):
        # Charger une image (remplacez le chemin par votre propre chemin d'image)
        image_path = "image_fusionnee.png"
        pixmap = QPixmap(image_path)
        self.image_label.setPixmap(pixmap)
        self.scroll_area.ensureWidgetVisible(self.image_label)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())



