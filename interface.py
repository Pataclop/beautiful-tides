import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel, QScrollArea, QAbstractItemView
from PyQt5.QtGui import QPixmap, QWheelEvent, QColor
from PyQt5.QtCore import Qt
from urllib.request import urlopen
import requests


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Sélecteur de mois")
        self.setGeometry(50, 50, 1700, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QHBoxLayout(self.central_widget)

        self.year_selector = QListWidget()
        self.year_selector.setFixedWidth(50)
        self.year_selector.addItems(["2022", "2023", "2024"]) # Ajoutez d'autres années si nécessaire
        self.year_selector.itemSelectionChanged.connect(self.on_month_selection_changed)


        self.month_list = QListWidget()
        self.month_list.setFixedWidth(100)
        self.month_list.addItems(["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"])
        self.month_list.setSelectionMode(QAbstractItemView.MultiSelection)

        

    

        
        


        self.scroll_area = QScrollArea()
        self.scroll_area.setFixedWidth(1500)
        self.scroll_area.setFixedHeight(600)
        self.scroll_area.setWidgetResizable(True)

        self.image_label = QLabel()
        self.scroll_area.setWidget(self.image_label)

        self.refresh_button = QPushButton("Rafraîchir")
        self.refresh_button.clicked.connect(self.refresh_image)


        self.print_button = QPushButton("print les mois")
        self.print_button.clicked.connect(self.print_selected_months)



        self.layout.addWidget(self.year_selector)
        self.layout.addWidget(self.month_list)
        
        self.image_layout = QVBoxLayout()
        self.image_layout.addWidget(self.scroll_area)
        self.image_layout.addWidget(self.refresh_button)
        self.layout.addLayout(self.image_layout)

    
    def print_selected_months(self):
        selected_months = [self.month_list.item(i).text() for i in range(self.month_list.count()) if self.month_list.item(i).isSelected()]
        print(selected_months)

    def on_month_selection_changed(self):
        selected_months = [self.month_list.item(i).text() for i in range(self.month_list.count()) if self.month_list.item(i).isSelected()]
        print(f"Mois sélectionnés : {selected_months}")

        for i in range(self.month_list.count()):
            item = self.month_list.item(i)
            item_name = self.month_list.item(i).text()
            year = self.year_selector.currentItem().text()
            url = f"https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees/le-verdon-sur-mer-1036/{item_name}-{year}"
            print (url)
            print (url)
            try:
                response = requests.head(url)
                if response.status_code == 200:
                    print("ok")
                    item.setForeground(QColor("green"))
                else:
                    print("not ok")
                    item.setForeground(QColor("red"))
            except:
                print("error")
                item.setForeground(QColor("red"))

    def refresh_image(self):
        # Charger une image (remplacez le chemin par votre propre chemin d'image)
        image_path = "juin-2024.png"
        pixmap = QPixmap(image_path)
        self.image_label.setPixmap(pixmap)
        self.scroll_area.ensureWidgetVisible(self.image_label)

    def wheelEvent(self, event: QWheelEvent):
        # Coefficients de zoom pour définir l'ampleur du zoom
        zoom_in_factor = 1.1
        zoom_out_factor = 0.9

        if event.angleDelta().y() > 0:
            # Zoom avant
            self.scroll_area.scale(zoom_in_factor, zoom_in_factor)
        else:
            # Zoom arrière
            self.scroll_area.scale(zoom_out_factor, zoom_out_factor)

        self.scroll_area.ensureVisible(self.image_label)

    def url_exists(self, url):
        try:
            urlopen(url)
            return True
        except:
            return False



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())



