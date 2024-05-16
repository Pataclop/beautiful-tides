import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel, QScrollArea, QAbstractItemView, QComboBox, QSlider
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

        self.comboBox = QComboBox(self)
        self.comboBox.addItem("Fond 1")
        self.comboBox.addItem("Fond 2")

        self.slider_hauteur_jour = QSlider(Qt.Horizontal)
        self.slider_hauteur_jour.setMinimum(-100)  # pour que chaque incrément corresponde à 0.1
        self.slider_hauteur_jour.setMaximum(100)   # pour que chaque incrément corresponde à 0.1
        self.slider_hauteur_jour.setValue(0)
        self.slider_hauteur_jour.setTickInterval(10)  # Chaque 1.0 sur le slider_hauteur_jour représentera 10 dixièmes
        self.slider_hauteur_jour.setTickPosition(QSlider.TicksBelow)
        self.slider_hauteur_jour.setFixedWidth(150)


        self.label_hauteur_jour = QLabel('Hauteur jour : 0.0')


        self.slider_epaisseur_trait_jour = QSlider(Qt.Horizontal)
        self.slider_epaisseur_trait_jour.setMinimum(-100)  # pour que chaque incrément corresponde à 0.1
        self.slider_epaisseur_trait_jour.setMaximum(100)   # pour que chaque incrément corresponde à 0.1
        self.slider_epaisseur_trait_jour.setValue(0)
        self.slider_epaisseur_trait_jour.setTickInterval(10)  # Chaque 1.0 sur le slider_hauteur_jour représentera 10 dixièmes
        self.slider_epaisseur_trait_jour.setTickPosition(QSlider.TicksBelow)
        self.slider_epaisseur_trait_jour.setFixedWidth(150)


        self.label_epaisseur_trait_jour = QLabel('Epaisseur trait jour : 0.0')


        self.slider_limite_haut_coef = QSlider(Qt.Horizontal)
        self.slider_limite_haut_coef.setMinimum(70)  # pour que chaque incrément corresponde à 0.1
        self.slider_limite_haut_coef.setMaximum(120)   # pour que chaque incrément corresponde à 0.1
        self.slider_limite_haut_coef.setValue(95)
        self.slider_limite_haut_coef.setTickInterval(1)  # Chaque 1.0 sur le slider_hauteur_jour dépassera 10 dixiemes
        self.slider_limite_haut_coef.setTickPosition(QSlider.TicksBelow)
        self.slider_limite_haut_coef.setFixedWidth(150)


        self.label_limite_haut_coef = QLabel('Limite haut coef : 0.0')

        self.slider_limite_bas_coef = QSlider(Qt.Horizontal)
        self.slider_limite_bas_coef.setMinimum(20)  # pour que chaque incrément corresponde à 0.1
        self.slider_limite_bas_coef.setMaximum(50)   # pour que chaque incrément corresponde à 0.1
        self.slider_limite_bas_coef.setValue(35)
        self.slider_limite_bas_coef.setTickInterval(1)  # Chaque 1.0 sur le slider_hauteur_jour dépassera 10 dixiemes
        self.slider_limite_bas_coef.setTickPosition(QSlider.TicksBelow)
        self.slider_limite_bas_coef.setFixedWidth(150)


        self.label_limite_bas_coef = QLabel('Limite bas coef : 0.0')

        self.slider_hauteur_jour.valueChanged.connect(self.updateLabel_hauteur_jour)
        self.slider_epaisseur_trait_jour.valueChanged.connect(self.updateLabel_epaisseur_trait_jour)
        self.slider_limite_haut_coef.valueChanged.connect(self.updateLabel_limite_haut_coef)
        self.slider_limite_bas_coef.valueChanged.connect(self.updateLabel_limite_bas_coef)



        self.print_button = QPushButton("Créer avec les mois sélectionnés")
        self.print_button.clicked.connect(self.print_selected_months)

        self.layout.addWidget(self.port_selector)
        self.layout.addWidget(self.year_selector)
        self.layout.addWidget(self.month_list)

     
        

#TODO il faut parametres pour personaliser un peu l'affichage. des optiopns (lune, saint, jsp), la police et la taile des éléments. 
#que tout soit personalisable. les couleurs aussi éventuellement. c'est une grosse interface mais c'estr bien quand meme. 

        self.image_layout = QVBoxLayout()
        self.image_layout.addWidget(self.scroll_area)
        self.comboBox.setFixedWidth(100)
        
        self.comboBox.setFocusPolicy(Qt.NoFocus)
        self.comboBox.setEnabled(False)

        
        vbox = QVBoxLayout()
        vbox.addWidget(self.label_hauteur_jour)
        vbox.addWidget(self.slider_hauteur_jour)
        vbox2 = QVBoxLayout()
        vbox2.addWidget(self.label_epaisseur_trait_jour)
        vbox2.addWidget(self.slider_epaisseur_trait_jour)
        vbox3 = QVBoxLayout()
        vbox3.addWidget(self.label_limite_haut_coef)
        vbox3.addWidget(self.slider_limite_haut_coef)
        vbox4 = QVBoxLayout()
        vbox4.addWidget(self.label_limite_bas_coef)
        vbox4.addWidget(self.slider_limite_bas_coef)
        hbox = QHBoxLayout()
        hbox.addWidget(self.comboBox)
        hbox.addLayout(vbox)
        hbox.addLayout(vbox2)
        hbox.addLayout(vbox3)
        hbox.addLayout(vbox4)

        self.image_layout.addLayout(hbox)

        self.setLayout(self.image_layout)

        self.image_layout.addWidget(self.preview_button)
        self.image_layout.addWidget(self.print_button)

        self.layout.addLayout(self.image_layout)
    
#TODO y'a des bugs ca se superpose je sais pas pouruqoi c'est bizarre, du a l'interface ? jsp. il est tard.
    def preview(self):
        selected_months = [[self.month_list.item(i).text() for i in range(self.month_list.count()) if self.month_list.item(i).isSelected()][0]]
        selected_port = self.port_selector.currentItem().text()

        print(f"Mois sélectionnés : {selected_months}")
        print(f"Port : {selected_port}")
        hauteur_jour = self.slider_hauteur_jour.value()
        epaisseur_trait_jour = self.slider_epaisseur_trait_jour.value()
        limite_haut_coef = self.slider_limite_haut_coef.value()
        limite_bas_coef = self.slider_limite_bas_coef.value()

        fonctions.creation_image_complete(selected_months, selected_port, 60, 1)
        self.refresh_image()

    def updateLabel_hauteur_jour(self):
            value = self.slider_hauteur_jour.value() / 10.0  # Convertit la valeur de l'intervalle [-100, 100] en [-10.0, 10.0]
            self.label_hauteur_jour.setText('hauteur jours : {:.1f}'.format(value))
    
    def updateLabel_epaisseur_trait_jour(self):
            value = self.slider_epaisseur_trait_jour.value() / 10.0  # Convertit la valeur de l'intervalle [-100, 100] en [-10.0, 10.0]
            self.label_epaisseur_trait_jour.setText('epaisseur trait jours : {:.1f}'.format(value))

    def updateLabel_limite_haut_coef(self):
            value = self.slider_limite_haut_coef.value()  # Convertit la valeur de l'intervalle [-100, 100] en [-10.0, 10.0]
            self.label_limite_haut_coef.setText('limite haut coef : {:.1f}'.format(value))
    
    def updateLabel_limite_bas_coef(self):
            value = self.slider_limite_bas_coef.value()  # Convertit la valeur de l'intervalle [-100, 100] en [-10.0, 10.0]
            self.label_limite_bas_coef.setText('limite bas coef : {:.1f}'.format(value))


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



