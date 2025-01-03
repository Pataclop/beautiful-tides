import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QListWidget, QPushButton, QProgressBar, QMessageBox, QComboBox, QLabel, QCheckBox, QGridLayout
import fonctions
import os

class PortsSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Ports Selector')
        self.setGeometry(100, 100, 300, 600)
        
        layout = QVBoxLayout()

        # Create a grid layout for better control over widget placement
        grid_layout = QGridLayout()
        
        # Create QListWidget for ports
        self.portListWidget = QListWidget()
        self.portListWidget.setSelectionMode(QListWidget.MultiSelection)
        
        # Load items from file
        with open('ports.txt', 'r') as file:
            ports = file.readlines()
            for port in ports:
                self.portListWidget.addItem(port.strip())
        
        # Create QListWidget for months
        self.monthListWidget = QListWidget()
        self.monthListWidget.setSelectionMode(QListWidget.MultiSelection)
        
        self.fondListWidget = QListWidget()
        self.fondListWidget.setSelectionMode(QListWidget.MultiSelection)
        
        months = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]
        for month in months:
            item = self.monthListWidget.addItem(month)
            self.monthListWidget.item(self.monthListWidget.count()-1).setSelected(True)
        
        fonds = ["zigzag vague", "bleu flou bulles", "bleu-gris plein", "orange plein", "kaki plein", "bleu vif plein", "bandes bleu orange kaki", "bandes vif"]
        for f in fonds:
            item = self.fondListWidget.addItem(str(f))
            self.fondListWidget.item(self.fondListWidget.count()-1).setSelected(False)
        
        # Create ComboBox for year selection
        self.yearComboBox = QComboBox()
        self.yearComboBox.addItems([str(year) for year in [2025]])
        
        # Create ComboBox for resolution selection
        self.resolutionComboBox = QComboBox()
        self.resolutionComboBox.addItems(['50', '150', '400', '600'])

        # Create Create button
        self.createButton = QPushButton('Create', self)
        self.createButton.clicked.connect(self.onCreate)
        
        # Create Progress Bar
        self.progressBar = QProgressBar(self)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(False)
        
        # Add widgets to the grid layout
        grid_layout.addWidget(QLabel('Select Ports:'), 0, 0)
        grid_layout.addWidget(self.portListWidget, 1, 0)
        grid_layout.addWidget(QLabel('Select Months:'), 2, 0)
        grid_layout.addWidget(self.monthListWidget, 3, 0)
        grid_layout.addWidget(QLabel('Select Year:'), 4, 0)
        grid_layout.addWidget(self.yearComboBox, 5, 0)
        grid_layout.addWidget(QLabel('Select Backgrounds:'), 6, 0)
        grid_layout.addWidget(self.fondListWidget, 7, 0)
        grid_layout.addWidget(QLabel('Select Resolution:'), 8, 0)
        grid_layout.addWidget(self.resolutionComboBox, 9, 0)
        grid_layout.addWidget(self.createButton, 10, 0)
        grid_layout.addWidget(self.progressBar, 11, 0)
        
        layout.addLayout(grid_layout)
        self.setLayout(layout)
        

    def update_progress(self):
        folder_path = 'IMAGES'
        file_count = len([name for name in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, name))])
        self.progress.setMaximum(file_count)
        self.progress.setValue(file_count)

    def onCreate(self):
        selected_ports = [item.text() for item in self.portListWidget.selectedItems()]
        selected_months = [item.text() for item in self.monthListWidget.selectedItems()]
        selected_year = self.yearComboBox.currentText()
        selected_resolution = self.resolutionComboBox.currentText()
        selected_fond = [self.fondListWidget.row(item) + 1 for item in self.fondListWidget.selectedItems()]

        self.progressBar.setMaximum(14)
        
        for index, port in enumerate(selected_ports):
            fonctions.creation_image_complete(selected_year, selected_months, port, int(selected_resolution), selected_fond, port + "_" + selected_year + ".png")
            self.progressBar.setValue(index + 1)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PortsSelector()
    ex.show()
    sys.exit(app.exec_())
