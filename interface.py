import sys
import sqlite3
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
                             QPushButton, QProgressBar, QMessageBox, QComboBox, QLabel,
                             QCheckBox, QGridLayout, QGroupBox, QTextEdit, QSpinBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
                             QFrame, QStatusBar, QTabWidget, QWidget as QtWidget)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor
import fonctions
import os
from datetime import datetime

# Liste prédéfinie des ports disponibles
AVAILABLE_PORTS = [
    ("Brest", "4"),
    ("Dunkerque", "7"),
    ("Paimpol", "957"),
    ("Loctudy", "987"),
    ("Lorient", "57"),
    ("Le Logeo", "1008"),
    ("Port Navalo", "1003"),
    ("Port du Crouesty", "1833"),
    ("Portivy", "998"),
    ("Port Maria", "999"),
    ("Port Haliguen", "1001"),
    ("Penerf", "1009"),
    ("Trehiguier", "1779"),
    ("Belle-Ile-le-Palais", "1000"),
    ("Ile de Houat", "1780"),
    ("Le de Hoedic", "1010"),
    ("Le Croizic", "1011"),
    ("Le Pouliguen", "1012"),
    ("Pornichet", "1013"),
    ("Saint-Nazaire", "21"),
    ("Le Grand Charpentier", "1014"),
    ("Pornic", "1020"),
    ("Pointe de Saint-Gildas", "1019"),
    ("Ile de Noirmoutier L'Herbaudiere", "1021"),
    ("Fromentine", "1022"),
    ("Ile d'Yeu Port Joinville", "1023"),
    ("Saint-Gilles-Croix-de-Vie", "1024"),
    ("Les Sables d'Olonne", "1025"),
    ("Ile de Re Saint-Martin", "1026"),
    ("La Rochelle Ville", "1027"),
    ("La Rochelle Pallice", "12"),
    ("Saint-Denis d'Oleron", "1067"),
    ("Ile d'Aix", "1028"),
    ("La Cotiniere", "1836"),
    ("Pointe de Gatseau", "1033"),
    ("Cordouan", "1034"),
    ("Royan", "1035"),
    ("Pointe de Grave", "59"),
    ("Le Verdon-sur-Mer", "1036"),
    ("Richard", "1037"),
    ("Lacanau", "1049"),
    ("Arcachon", "1046"),
    ("Cap Ferret", "1045"),
    ("Biscarosse", "1050"),
    ("Mimizan", "1051"),
    ("Vieux-Boucau", "1052"),
    ("Boucau", "46"),
    ("Saint-Jean-de-Luz", "61"),
]

class DataFetcherThread(QThread):
    """Thread pour récupérer les données en arrière-plan"""
    progress = pyqtSignal(str)  # Signal pour les messages de progression
    finished = pyqtSignal(bool, str)  # Signal quand terminé (succès, message)

    def __init__(self, port_code, port_name, month, year):
        super().__init__()
        self.port_code = port_code
        self.port_name = port_name
        self.month = month
        self.year = year

    def run(self):
        try:
            self.progress.emit(f"Récupération des données pour {self.port_name} {self.month}/{self.year}...")

            # Appeler la fonction de récupération
            port_full = f"{self.port_name.lower().replace(' ', '-')}-{self.port_code}"
            result = fonctions.recuperation_et_sauvegarde_url(
                'https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees',
                port_full,
                self.month,
                self.year
            )

            if result:
                self.progress.emit("Données récupérées avec succès !")
                self.finished.emit(True, f"Données pour {self.port_name} {self.month}/{self.year} récupérées")
            else:
                self.finished.emit(False, f"Échec de récupération pour {self.port_name} {self.month}/{self.year}")

        except Exception as e:
            self.finished.emit(False, f"Erreur: {str(e)}")

class BeautifulTidesInterface(QWidget):
    def __init__(self):
        super().__init__()
        self.current_year = datetime.now().year
        self.initUI()

    def initUI(self):
        self.setWindowTitle('🌊 Beautiful Tides - Générateur de Calendriers de Marées')
        self.setGeometry(200, 200, 800, 600)

        # Style moderne
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #007bff;
                border-radius: 8px;
                margin-top: 1ex;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: #007bff;
                font-size: 14px;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
            QComboBox {
                border: 2px solid #ced4da;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
                min-width: 120px;
            }
            QComboBox:hover {
                border-color: #007bff;
            }
            QSpinBox {
                border: 2px solid #ced4da;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
                min-width: 80px;
            }
            QSpinBox:hover {
                border-color: #007bff;
            }
            QLabel {
                color: #495057;
                font-size: 13px;
            }
            QProgressBar {
                border: 2px solid #ced4da;
                border-radius: 4px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 2px;
            }
            QTextEdit {
                border: 2px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
        """)

        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Titre principal
        title_label = QLabel("🗓️ Générateur de Calendriers de Marées")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
            margin-bottom: 10px;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Création de l'interface simplifiée
        main_container = self.create_simple_calendar_interface()
        main_layout.addWidget(main_container)

        self.setLayout(main_layout)

        # Charger les ports au démarrage
        QTimer.singleShot(100, self.load_ports)

    def create_simple_calendar_interface(self):
        """Créer l'interface ultra-simplifiée pour la génération de calendriers"""
        # Conteneur principal avec style moderne
        main_container = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Section Configuration
        config_group = QGroupBox("⚙️ Configuration")
        config_layout = QHBoxLayout()
        config_layout.setSpacing(20)

        # Port
        port_layout = QVBoxLayout()
        port_label = QLabel("🏖️ Port")
        self.cal_port_combo = QComboBox()
        self.all_ports_checkbox = QCheckBox("Tous les ports")
        self.all_ports_checkbox.setToolTip("Générer le calendrier pour tous les ports disponibles")
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.cal_port_combo)
        port_layout.addWidget(self.all_ports_checkbox)
        config_layout.addLayout(port_layout)

        # Connecter la checkbox pour désactiver/activer le combo
        self.all_ports_checkbox.toggled.connect(self.on_all_ports_toggled)

        # Année
        year_layout = QVBoxLayout()
        year_label = QLabel("📅 Année")
        self.cal_year_spin = QSpinBox()
        self.cal_year_spin.setRange(2020, 2030)
        self.cal_year_spin.setValue(self.current_year)
        year_layout.addWidget(year_label)
        year_layout.addWidget(self.cal_year_spin)
        config_layout.addLayout(year_layout)

        # Taille (DPI)
        size_layout = QVBoxLayout()
        size_label = QLabel("📏 Taille (pixels)")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(50, 500)
        self.size_spin.setValue(100)
        self.size_spin.setSingleStep(50)
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_spin)
        config_layout.addLayout(size_layout)

        # Fond
        fond_layout = QVBoxLayout()
        fond_label = QLabel("🎨 Fond")
        self.fond_combo = QComboBox()
        fonds = ['1', '2', '3', '4', '5', '6', '7', '8']
        self.fond_combo.addItems(fonds)
        self.fond_combo.setCurrentText('7')
        fond_layout.addWidget(fond_label)
        fond_layout.addWidget(self.fond_combo)
        config_layout.addLayout(fond_layout)

        config_layout.addStretch()
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Bouton principal de génération
        self.generate_btn = QPushButton("🚀 Générer le Calendrier")
        self.generate_btn.setMinimumHeight(50)
        self.generate_btn.clicked.connect(self.generer_calendrier_avec_recuperation_auto)
        layout.addWidget(self.generate_btn)

        # Section Progression
        progress_group = QGroupBox("📊 Progression")
        progress_layout = QVBoxLayout()

        self.cal_progress_bar = QProgressBar()
        self.cal_progress_bar.setVisible(False)
        self.cal_progress_bar.setMinimumHeight(25)
        progress_layout.addWidget(self.cal_progress_bar)

        self.progress_details = QLabel("Prêt à générer votre calendrier")
        self.progress_details.setStyleSheet("color: #6c757d; font-style: italic;")
        self.progress_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.progress_details)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Section Résultats
        results_group = QGroupBox("📋 Résultats")
        results_layout = QVBoxLayout()

        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(200)
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        main_container.setLayout(layout)

        # Retourner le conteneur pour l'ajouter dans initUI
        return main_container

    def generer_calendriers_tous_ports(self):
        """Générer le calendrier pour tous les ports disponibles"""
        year = self.cal_year_spin.value()
        size = self.size_spin.value()
        fond = self.fond_combo.currentText()

        # Tous les mois de l'année
        all_months = ['janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin',
                     'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre']

        # Désactiver le bouton pendant le processus
        self.generate_btn.setEnabled(False)
        self.cal_progress_bar.setVisible(True)

        total_operations = len(AVAILABLE_PORTS) * (len(all_months) + 1)  # +1 pour la génération
        self.cal_progress_bar.setRange(0, total_operations)
        self.cal_progress_bar.setValue(0)

        self.results_text.clear()
        self.results_text.append(f"📅 Génération calendriers pour TOUS LES PORTS {year}")
        self.results_text.append(f"Configuration: {size}px, Fond {fond}")
        self.results_text.append(f"Nombre de ports: {len(AVAILABLE_PORTS)}")
        self.results_text.append("")

        operation_count = 0

        try:
            for port_idx, (port_name, port_code) in enumerate(AVAILABLE_PORTS):
                self.results_text.append(f"🏖️ Port {port_idx+1}/{len(AVAILABLE_PORTS)}: {port_name}")
                self.progress_details.setText(f"Traitement: {port_name}")

                # S'assurer que le port existe dans la base de données
                if not self.ensure_port_in_db(port_name, port_code):
                    self.results_text.append(f"  ❌ Impossible d'ajouter le port {port_name}")
                    continue

                # Vérifier et récupérer les données manquantes
                missing_months = []
                for month in all_months:
                    month_num = fonctions.MONTH_MAPPING.get(month, str(all_months.index(month) + 1).zfill(2))
                    has_data, is_complete, _, _ = fonctions.check_complete_month_data(port_code, month_num, str(year))

                    if not is_complete:
                        missing_months.append(month)

                    operation_count += 1
                    self.cal_progress_bar.setValue(operation_count)

                # Récupérer les données manquantes
                if missing_months:
                    self.results_text.append(f"  📥 Récupération de {len(missing_months)} mois...")
                    for month in missing_months:
                        port_formatted = f"{port_name.lower().replace(' ', '-')}-{port_code}"
                        result = fonctions.recuperation_et_sauvegarde_url(
                            'https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees',
                            port_formatted,
                            month,
                            str(year)
                        )
                        if not result:
                            self.results_text.append(f"    ❌ Échec: {month}")

                # Générer le calendrier pour ce port
                self.results_text.append("  🎨 Génération du calendrier...")
                port_formatted = f"{port_name.lower().replace(' ', '-')}-{port_code}"
                output_name = f"{port_name.lower().replace(' ', '_')}_{year}.png"
                fonctions.creation_image_complete(str(year), all_months, port_formatted, size, fond, output_name)

                self.results_text.append(f"  ✅ Terminé: {output_name}")
                operation_count += 1
                self.cal_progress_bar.setValue(operation_count)

            self.cal_progress_bar.setValue(total_operations)
            self.progress_details.setText("Terminé pour tous les ports !")

            self.results_text.append("")
            self.results_text.append("🎉 Génération terminée pour tous les ports !")

            # Ouvrir le dossier de sortie
            output_dir = "OUTPUT IMAGES"
            if os.path.exists(output_dir):
                os.startfile(output_dir)

        except Exception as e:
            self.results_text.append(f"❌ Erreur générale: {e}")
            QMessageBox.critical(self, 'Erreur', f'Erreur lors du processus: {e}')

        finally:
            self.generate_btn.setEnabled(True)
            self.cal_progress_bar.setVisible(False)
            self.progress_details.setText("Prêt")

    def on_all_ports_toggled(self, checked):
        """Appelé quand la checkbox 'Tous les ports' change"""
        self.cal_port_combo.setEnabled(not checked)
        if checked:
            self.cal_port_combo.setCurrentIndex(-1)  # Aucun port sélectionné

        """Créer l'onglet de génération de calendriers"""
        calendar_tab = QtWidget()
        layout = QVBoxLayout()

        # Titre
        title = QLabel("🗓️ Génération de calendriers")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # Configuration simple
        config_group = QGroupBox("Configuration")
        config_layout = QHBoxLayout()

        # Port
        config_layout.addWidget(QLabel("Port:"))
        self.cal_port_combo = QComboBox()
        config_layout.addWidget(self.cal_port_combo)

        # Année
        config_layout.addWidget(QLabel("Année:"))
        self.cal_year_spin = QSpinBox()
        self.cal_year_spin.setRange(2020, 2030)
        self.cal_year_spin.setValue(self.current_year)
        config_layout.addWidget(self.cal_year_spin)

        # Taille
        config_layout.addWidget(QLabel("Taille (px):"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(50, 500)
        self.size_spin.setSingleStep(50)  # Pas de 50 pour atteindre facilement les seuils
        self.size_spin.setValue(100)
        config_layout.addWidget(self.size_spin)

        # Fond
        config_layout.addWidget(QLabel("Fond:"))
        self.fond_combo = QComboBox()
        fonds = ['1', '2', '3', '4', '5', '6', '7', '8']
        self.fond_combo.addItems(fonds)
        self.fond_combo.setCurrentText('7')
        config_layout.addWidget(self.fond_combo)

        config_layout.addStretch()
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Bouton de génération
        self.generate_btn = QPushButton("🎨 Générer le calendrier")
        self.generate_btn.clicked.connect(self.generer_calendrier_avec_recuperation_auto)
        layout.addWidget(self.generate_btn)

        # Barre de progression détaillée
        progress_group = QGroupBox("Progression")
        progress_layout = QVBoxLayout()

        self.cal_progress_bar = QProgressBar()
        self.cal_progress_bar.setVisible(False)
        progress_layout.addWidget(self.cal_progress_bar)

        self.progress_details = QLabel("Prêt")
        progress_layout.addWidget(self.progress_details)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Résultats
        results_group = QGroupBox("Résultats")
        results_layout = QVBoxLayout()
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(100)
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        calendar_tab.setLayout(layout)



    def load_ports(self):
        """Charger la liste des ports dans le combo box"""
        try:
            # Vider le combo box
            self.cal_port_combo.clear()

            # Ajouter tous les ports disponibles
            for port_name, port_code in AVAILABLE_PORTS:
                display_text = f"{port_name} ({port_code})"
                self.cal_port_combo.addItem(display_text, (port_name, port_code))

            # Sélectionner Vieux-Boucau par défaut
            self.cal_port_combo.setCurrentIndex(len(AVAILABLE_PORTS) - 1)  # Vieux-Boucau

        except Exception as e:
            QMessageBox.critical(self, 'Erreur', f'Erreur lors du chargement des ports: {e}')

    def ensure_port_in_db(self, port_name, port_code):
        """S'assurer qu'un port existe dans la base de données"""
        try:
            conn = sqlite3.connect('tides_database.db')
            cursor = conn.cursor()

            # Vérifier si le port existe
            cursor.execute('SELECT id FROM ports WHERE port_code = ?', (port_code,))
            existing = cursor.fetchone()

            if not existing:
                # Ajouter le port s'il n'existe pas
                cursor.execute('INSERT INTO ports (port_name, port_code) VALUES (?, ?)',
                             (port_name, port_code))
                conn.commit()
                # Port ajouté silencieusement

            conn.close()
            return True

        except sqlite3.Error as e:
            # Erreur lors de l'ajout du port (silencieuse)
            return False






    def on_fetch_progress(self, message):
        """Callback pour les messages de progression"""
        self.results_text.append(message)
        self.progress_details.setText(message)

    def on_fetch_finished(self, success, message):
        """Callback quand la récupération est terminée"""
        if success:
            self.results_text.append(f"✅ {message}")
            self.progress_details.setText("Terminé avec succès")
        else:
            self.results_text.append(f"❌ {message}")
            self.progress_details.setText("Échec")
            QMessageBox.warning(self, 'Erreur', message)

        # Mettre à jour l'état des données
        self.mettre_a_jour_statut_donnees_selectionnees()

    def generer_calendrier_avec_recuperation_auto(self):
        """Générer le calendrier avec récupération automatique des données manquantes"""
        all_ports = self.all_ports_checkbox.isChecked()

        if all_ports:
            # Générer pour tous les ports
            self.generer_calendriers_tous_ports()
            return

        # Générer pour un seul port
        if self.cal_port_combo.currentData() is None:
            QMessageBox.warning(self, 'Erreur', 'Veuillez sélectionner un port.')
            return

        port_name, port_code = self.cal_port_combo.currentData()

        # S'assurer que le port existe dans la base de données
        if not self.ensure_port_in_db(port_name, port_code):
            QMessageBox.warning(self, 'Erreur', f'Impossible d\'ajouter le port {port_name} à la base de données.')
            return

        year = self.cal_year_spin.value()
        size = self.size_spin.value()
        fond = self.fond_combo.currentText()

        # Tous les mois de l'année
        all_months = ['janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin',
                     'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre']

        # Désactiver le bouton pendant le processus
        self.generate_btn.setEnabled(False)
        self.cal_progress_bar.setVisible(True)
        self.cal_progress_bar.setRange(0, len(all_months) + 1)  # +1 pour la génération finale
        self.cal_progress_bar.setValue(0)

        self.results_text.clear()
        self.results_text.append(f"📅 Génération calendrier {port_name} {year}")
        self.results_text.append(f"Configuration: {size}px, Fond {fond}")
        self.results_text.append("")

        self.progress_details.setText("Vérification des données existantes...")

        try:
            # Vérifier et récupérer les données manquantes mois par mois
            missing_months = []
            for i, month in enumerate(all_months):
                month_num = fonctions.MONTH_MAPPING.get(month, str(all_months.index(month) + 1).zfill(2))
                has_data, is_complete, _, _ = fonctions.check_complete_month_data(port_code, month_num, str(year))

                if not is_complete:
                    missing_months.append(month)

                self.cal_progress_bar.setValue(i + 1)
                self.progress_details.setText(f"Vérification: {month} - {'✅' if is_complete else '❌'}")

            # Récupérer les données manquantes
            if missing_months:
                self.results_text.append(f"📥 Récupération de {len(missing_months)} mois manquants...")
                self.progress_details.setText(f"Récupération de {len(missing_months)} mois...")

                for month in missing_months:
                    self.results_text.append(f"  Téléchargement: {month}...")
                    self.progress_details.setText(f"Récupération: {month}...")

                    port_formatted = f"{port_name.lower().replace(' ', '-')}-{port_code}"
                    result = fonctions.recuperation_et_sauvegarde_url(
                        'https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees',
                        port_formatted,
                        month,
                        str(year)
                    )

                    if result:
                        self.results_text.append(f"  ✅ {month}: OK")
                    else:
                        self.results_text.append(f"  ❌ {month}: Échec")

            # Générer le calendrier avec tous les mois
            self.progress_details.setText("Génération du calendrier...")
            self.results_text.append("")
            self.results_text.append("🎨 Génération du calendrier...")

            port_formatted = f"{port_name.lower().replace(' ', '-')}-{port_code}"
            output_name = f"{port_name.lower().replace(' ', '_')}_{year}.png"
            fonctions.creation_image_complete(str(year), all_months, port_formatted, size, fond, output_name)

            self.cal_progress_bar.setValue(len(all_months) + 1)
            self.progress_details.setText("Terminé !")

            self.results_text.append("✅ Calendrier généré avec succès !")
            self.results_text.append(f"📁 Fichier: {output_name}")

            # Ouvrir le dossier de sortie
            output_dir = "OUTPUT IMAGES"
            if os.path.exists(output_dir):
                os.startfile(output_dir)

        except Exception as e:
            self.results_text.append(f"❌ Erreur: {e}")
            QMessageBox.critical(self, 'Erreur', f'Erreur lors du processus: {e}')

        finally:
            self.generate_btn.setEnabled(True)
            self.cal_progress_bar.setVisible(False)
            self.progress_details.setText("Prêt")



    def log_message(self, message):
        """Ajouter un message aux logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs_text.append(f"[{timestamp}] {message}")

        # Scroll to bottom
        scrollbar = self.logs_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Initialiser la base de données
    fonctions.init_database()

    # Créer et afficher la nouvelle interface
    interface = BeautifulTidesInterface()
    interface.show()

    sys.exit(app.exec())
