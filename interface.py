#!/usr/bin/env python3
"""Beautiful Tides - interface graphique (PyQt6).

Fonctionnalites :
  - Onglet Generer : carte des ports (Leaflet en ligne ou carte hors-ligne),
    recherche, galerie de fonds avec apercu, choix des mois, multi-fonds,
    taille, generation en tache de fond (sans gel) avec progression.
  - Onglet Base de donnees : remplissage de la base pour une annee (mois futurs
    uniquement), sans generer d'images, avec progression et annulation.
  - Onglet Ajouter un port / A propos.

L'interface n'importe le moteur de rendu (matplotlib/cv2) que lors de la
generation (import differe) : demarrage rapide et robuste.
"""
import os
import sys
import time
import subprocess

# QtWebEngine (carte Leaflet) DOIT etre importe avant la creation du QApplication,
# sinon son initialisation echoue et on bascule inutilement sur la carte hors-ligne.
try:
    from PyQt6 import QtWebEngineWidgets  # noqa: F401
except Exception:
    pass

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox, QLineEdit, QGroupBox,
    QProgressBar, QTextEdit, QTabWidget, QListWidget, QListWidgetItem, QMessageBox,
    QSplitter, QFileDialog, QFormLayout,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

import db
import ports as ports_module
import scrap_all
from ui.fond_gallery import FondGallery
from ui.map_widget import create_port_map

URL_BASE = "https://marine.meteoconsult.fr/meteo-marine/horaires-des-marees"
MONTHS_FR = db.MONTHS_FR
OUTPUT_DIR = "OUTPUT IMAGES"


def open_folder(path):
    """Ouvre un dossier dans l'explorateur, multiplateforme."""
    try:
        if not os.path.isdir(path):
            return
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif os.name == "nt":
            os.startfile(path)  # noqa: pylint - Windows uniquement
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Threads de travail
# ---------------------------------------------------------------------------
class GenerationWorker(QThread):
    progress = pyqtSignal(int, int, str)
    log = pyqtSignal(str)
    finished_ok = pyqtSignal(bool, str)

    def __init__(self, targets, year, months, size, fonds):
        super().__init__()
        self.targets = targets      # liste de dicts port
        self.year = str(year)
        self.months = list(months)
        self.size = int(size)
        self.fonds = list(fonds)
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            import fonctions  # import differe (charge matplotlib/cv2)
        except Exception as e:
            self.finished_ok.emit(False, f"Impossible de charger le moteur de rendu : {e}")
            return

        db.init_database()
        total = len(self.targets)
        generated = 0
        for idx, port in enumerate(self.targets, 1):
            if self._cancel:
                self.finished_ok.emit(False, "Annule.")
                return
            name, code = port["name"], str(port["code"])
            self.progress.emit(idx - 1, total, f"{name} : preparation des donnees...")
            db.ensure_port_in_db(name, code)
            slug = ports_module.port_slug(name, code)

            # Determiner les mois disponibles (recuperer les mois FUTURS manquants).
            available = []
            fetchable_future = set(db.future_months(self.year, self.months))
            for m in self.months:
                mnum = db.MONTH_MAPPING.get(m, m)
                _, complete, _, _ = db.check_complete_month_data(code, mnum, self.year)
                if complete:
                    available.append(m)
                elif m in fetchable_future:
                    self.log.emit(f"  telechargement {name} {m}...")
                    try:
                        res = db.recuperation_et_sauvegarde_url(URL_BASE, slug, m, self.year)
                    except Exception as e:
                        res = None
                        self.log.emit(f"  erreur {m}: {e}")
                    if res and res.strip():
                        available.append(m)
                    else:
                        self.log.emit(f"  {m}: donnees indisponibles (mois trop lointain ?) - ignore")
                    time.sleep(2.0)  # courtoisie : limite de frequence du site
                else:
                    self.log.emit(f"  {m}: mois passe absent de la base (ignore)")

            if not available:
                self.log.emit(f"{name} : aucune donnee disponible, port ignore.")
                continue

            self.progress.emit(idx - 1, total, f"{name} : generation ({len(available)} mois)...")
            output_name = f"{name.lower().replace(' ', '_')}_{self.year}.png"
            try:
                fonctions.creation_image_complete(
                    self.year, available, slug, self.size, self.fonds, output_name)
                generated += 1
                self.log.emit(f"{name} : OK -> {len(self.fonds)} image(s)")
            except Exception as e:
                self.log.emit(f"{name} : ERREUR de generation : {e}")
            self.progress.emit(idx, total, f"{name} : termine")

        if generated:
            self.finished_ok.emit(True, f"{generated}/{total} port(s) generes.")
        else:
            self.finished_ok.emit(False, "Aucune image generee (donnees manquantes ?).")


class FillDbWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished_ok = pyqtSignal(bool, str)

    def __init__(self, targets, pump=True, year=None):
        super().__init__()
        self.targets = targets
        self.pump = pump
        self.year = str(year) if year else None
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            if self.pump:
                stats = scrap_all.pump_future(
                    ports=self.targets,
                    progress_cb=lambda d, t, m: self.progress.emit(d, t, m),
                    cancel=lambda: self._cancel,
                )
                msg = (f"Termine : {stats['success']} mois récupérés, "
                       f"{stats['skipped']} déjà complets, {stats['errors']} indisponibles "
                       f"sur {stats['ports']} ports (en {stats['duration_s']:.0f}s).")
            else:
                stats = scrap_all.fill_database(
                    self.year, ports=self.targets,
                    progress_cb=lambda d, t, m: self.progress.emit(d, t, m),
                    cancel=lambda: self._cancel,
                )
                msg = (f"Termine : {stats['success']} OK, {stats['skipped']} déjà complets, "
                       f"{stats['errors']} échecs sur {stats['total']} (en {stats['duration_s']:.0f}s).")
            self.finished_ok.emit(True, msg)
        except Exception as e:
            self.finished_ok.emit(False, f"Erreur : {e}")


# ---------------------------------------------------------------------------
# Selecteur de mois
# ---------------------------------------------------------------------------
class MonthSelector(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.checks = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        grid = QGridLayout()
        grid.setSpacing(2)
        for i, m in enumerate(MONTHS_FR):
            cb = QCheckBox(m.capitalize())
            cb.setChecked(True)
            self.checks[m] = cb
            grid.addWidget(cb, i // 3, i % 3)
        lay.addLayout(grid)
        btns = QHBoxLayout()
        for label, fn in [("Tous", self._all), ("Aucun", self._none), ("A venir", self._future)]:
            b = QPushButton(label)
            b.setMaximumHeight(26)
            b.clicked.connect(fn)
            btns.addWidget(b)
        lay.addLayout(btns)

    def _all(self):
        for cb in self.checks.values():
            cb.setChecked(True)

    def _none(self):
        for cb in self.checks.values():
            cb.setChecked(False)

    def _future(self):
        year = self.window().current_year() if hasattr(self.window(), "current_year") else None
        fut = set(db.future_months(year)) if year else set(MONTHS_FR)
        for m, cb in self.checks.items():
            cb.setChecked(m in fut)

    def selected(self):
        return [m for m in MONTHS_FR if self.checks[m].isChecked()]


# ---------------------------------------------------------------------------
# Fenetre principale
# ---------------------------------------------------------------------------
class BeautifulTides(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ports = ports_module.load_ports()
        self.selected_port = None
        self._gen_worker = None
        self._fill_worker = None
        self.setWindowTitle("🌊 Beautiful Tides")
        self.resize(1180, 760)
        self._build_ui()

    def current_year(self):
        return self.year_spin.value()

    # ---- construction ----
    def _build_ui(self):
        self.setStyleSheet(STYLE)
        tabs = QTabWidget()
        tabs.addTab(self._build_generate_tab(), "🎨  Générer")
        tabs.addTab(self._build_db_tab(), "🗄️  Base de données")
        tabs.addTab(self._build_ports_tab(), "➕  Ports")
        tabs.addTab(self._build_about_tab(), "ℹ️  À propos")
        self.setCentralWidget(tabs)

    def _build_generate_tab(self):
        w = QWidget()
        outer = QHBoxLayout(w)
        split = QSplitter(Qt.Orientation.Horizontal)

        # --- gauche : carte + recherche + liste ---
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.addWidget(QLabel("<b>Choix du port</b>"))
        self.map_widget, online = create_port_map(self.ports)
        self.map_widget.portSelected.connect(self._on_port_selected)
        lv.addWidget(self.map_widget, 1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher un port...")
        self.search.textChanged.connect(self._filter_ports)
        lv.addWidget(self.search)

        self.port_list = QListWidget()
        self.port_list.setMaximumHeight(160)
        self._fill_port_list(self.ports)
        self.port_list.itemClicked.connect(self._on_list_clicked)
        lv.addWidget(self.port_list)

        self.all_ports_cb = QCheckBox("Générer pour TOUS les ports")
        lv.addWidget(self.all_ports_cb)

        map_note = "Carte en ligne (OpenStreetMap)" if online else "Carte hors-ligne"
        note = QLabel(map_note)
        note.setStyleSheet("color:#6c757d; font-size:11px;")
        lv.addWidget(note)

        # --- droite : options ---
        right = QWidget()
        rv = QVBoxLayout(right)

        cfg = QGroupBox("Configuration")
        form = QFormLayout(cfg)
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2020, 2035)
        from datetime import datetime
        self.year_spin.setValue(datetime.now().year)
        form.addRow("Année", self.year_spin)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(50, 500)
        self.size_spin.setSingleStep(25)
        self.size_spin.setValue(100)
        self.size_spin.setToolTip("Résolution (DPI). 100 = qualité standard, plus = plus grand/lent.")
        form.addRow("Taille (px)", self.size_spin)

        self.month_selector = MonthSelector()
        form.addRow("Mois", self.month_selector)
        rv.addWidget(cfg)

        fond_box = QGroupBox("Fond (cliquer pour choisir ; Ctrl+clic = plusieurs)")
        fbl = QVBoxLayout(fond_box)
        self.fond_gallery = FondGallery(multi=True, columns=4)
        self.fond_gallery.set_selected(["7"])
        fbl.addWidget(self.fond_gallery)
        rv.addWidget(fond_box, 1)

        self.generate_btn = QPushButton("🚀  Générer le calendrier")
        self.generate_btn.setObjectName("primary")
        self.generate_btn.setMinimumHeight(46)
        self.generate_btn.clicked.connect(self._start_generation)
        rv.addWidget(self.generate_btn)

        self.gen_progress = QProgressBar()
        self.gen_progress.setVisible(False)
        rv.addWidget(self.gen_progress)
        self.gen_status = QLabel("Prêt.")
        self.gen_status.setStyleSheet("color:#6c757d;")
        rv.addWidget(self.gen_status)

        self.gen_log = QTextEdit()
        self.gen_log.setReadOnly(True)
        self.gen_log.setMaximumHeight(150)
        rv.addWidget(self.gen_log)

        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([440, 720])
        outer.addWidget(split)
        return w

    def _build_db_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("<b>Aspirer les données de marées</b> (télécharge et stocke, "
                           "sans générer d'images)"))
        info = QLabel("Pour chaque port, télécharge <b>tous les mois à venir</b> "
                      "(mois courant puis suivants, sur plusieurs années) jusqu'à "
                      "l'horizon publié par le site. Les mois déjà en base sont ignorés. "
                      "Un délai entre requêtes respecte la limite de fréquence du site.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#6c757d;")
        v.addWidget(info)

        row = QHBoxLayout()
        self.db_all_cb = QCheckBox("Tous les ports")
        self.db_all_cb.setChecked(True)
        row.addWidget(self.db_all_cb)
        row.addStretch()
        self.fill_btn = QPushButton("📥  Aspirer tout le possible")
        self.fill_btn.setObjectName("primary")
        self.fill_btn.clicked.connect(self._start_fill)
        row.addWidget(self.fill_btn)
        self.fill_cancel_btn = QPushButton("Annuler")
        self.fill_cancel_btn.setEnabled(False)
        self.fill_cancel_btn.clicked.connect(self._cancel_fill)
        row.addWidget(self.fill_cancel_btn)
        v.addLayout(row)

        self.fill_progress = QProgressBar()
        self.fill_progress.setVisible(False)
        v.addWidget(self.fill_progress)
        self.fill_status = QLabel("Prêt.")
        self.fill_status.setStyleSheet("color:#6c757d;")
        v.addWidget(self.fill_status)

        self.fill_log = QTextEdit()
        self.fill_log.setReadOnly(True)
        v.addWidget(self.fill_log, 1)
        return w

    def _build_ports_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("<b>Ajouter un port</b>"))
        v.addWidget(QLabel("Le code est l'identifiant meteoconsult (dernier nombre de l'URL "
                           "horaires-des-marees/&lt;nom&gt;-&lt;code&gt;)."))
        form = QFormLayout()
        self.np_name = QLineEdit()
        self.np_code = QLineEdit()
        self.np_lat = QLineEdit()
        self.np_lon = QLineEdit()
        self.np_region = QLineEdit()
        self.np_coast = QComboBox()
        self.np_coast.addItems(["Atlantique", "Manche", "Mer du Nord", "Mediterranee", "Corse"])
        form.addRow("Nom", self.np_name)
        form.addRow("Code meteoconsult", self.np_code)
        form.addRow("Latitude (optionnel)", self.np_lat)
        form.addRow("Longitude (optionnel)", self.np_lon)
        form.addRow("Région (optionnel)", self.np_region)
        form.addRow("Côte", self.np_coast)
        v.addLayout(form)
        add_btn = QPushButton("➕  Ajouter le port")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_port)
        v.addWidget(add_btn)
        self.ports_info = QLabel(f"{len(self.ports)} ports actuellement disponibles.")
        self.ports_info.setStyleSheet("color:#6c757d;")
        v.addWidget(self.ports_info)
        v.addStretch()
        return w

    def _build_about_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        txt = QLabel(
            "<h2>🌊 Beautiful Tides</h2>"
            "<p>Génère des affiches annuelles de calendriers de marées pour les ports français.</p>"
            "<p><b>Données :</b> marine.meteoconsult.fr (stockées en base SQLite locale).</p>"
            f"<p><b>Dossier de sortie :</b> {os.path.abspath(OUTPUT_DIR)}</p>"
            "<p>Astuce : choisissez le port sur la carte, un ou plusieurs fonds, puis Générer.</p>")
        txt.setWordWrap(True)
        txt.setTextFormat(Qt.TextFormat.RichText)
        v.addWidget(txt)
        open_btn = QPushButton("📁  Ouvrir le dossier de sortie")
        open_btn.clicked.connect(lambda: open_folder(OUTPUT_DIR))
        v.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        v.addStretch()
        return w

    # ---- selection des ports ----
    def _fill_port_list(self, ports):
        self.port_list.clear()
        for p in ports:
            item = QListWidgetItem(f"{p['name']}  ({p['coast']})")
            item.setData(Qt.ItemDataRole.UserRole, p)
            self.port_list.addItem(item)

    def _filter_ports(self, text):
        text = text.strip().lower()
        filtered = [p for p in self.ports if text in p["name"].lower()] if text else self.ports
        self._fill_port_list(filtered)

    def _on_list_clicked(self, item):
        p = item.data(Qt.ItemDataRole.UserRole)
        self._set_selected_port(p)
        if hasattr(self.map_widget, "select_code"):
            self.map_widget.select_code(p["code"])

    def _on_port_selected(self, p):
        self._set_selected_port(p)

    def _set_selected_port(self, p):
        self.selected_port = p
        self.gen_status.setText(f"Port sélectionné : {p['name']}")

    # ---- generation ----
    def _start_generation(self):
        if self._gen_worker and self._gen_worker.isRunning():
            return
        fonds = self.fond_gallery.selected_ids()
        if not fonds:
            QMessageBox.warning(self, "Fond", "Choisissez au moins un fond.")
            return
        months = self.month_selector.selected()
        if not months:
            QMessageBox.warning(self, "Mois", "Choisissez au moins un mois.")
            return

        if self.all_ports_cb.isChecked():
            targets = list(self.ports)
        elif self.selected_port:
            targets = [self.selected_port]
        else:
            QMessageBox.warning(self, "Port", "Choisissez un port (carte ou liste) "
                                              "ou cochez « Tous les ports ».")
            return

        self.gen_log.clear()
        self.gen_progress.setVisible(True)
        self.gen_progress.setRange(0, len(targets))
        self.gen_progress.setValue(0)
        self.generate_btn.setEnabled(False)

        self._gen_worker = GenerationWorker(
            targets, self.year_spin.value(), months, self.size_spin.value(), fonds)
        self._gen_worker.progress.connect(self._on_gen_progress)
        self._gen_worker.log.connect(self.gen_log.append)
        self._gen_worker.finished_ok.connect(self._on_gen_finished)
        self._gen_worker.start()

    def _on_gen_progress(self, done, total, msg):
        self.gen_progress.setMaximum(total)
        self.gen_progress.setValue(done)
        self.gen_status.setText(msg)

    def _on_gen_finished(self, ok, msg):
        self.gen_progress.setVisible(False)
        self.generate_btn.setEnabled(True)
        self.gen_status.setText(msg)
        self.gen_log.append(("✅ " if ok else "⚠️ ") + msg)
        if ok:
            open_folder(OUTPUT_DIR)

    # ---- remplissage base ----
    def _start_fill(self):
        if self._fill_worker and self._fill_worker.isRunning():
            return
        if self.db_all_cb.isChecked() or not self.selected_port:
            targets = list(self.ports)
        else:
            targets = [self.selected_port]
        self.fill_log.clear()
        self.fill_progress.setVisible(True)
        self.fill_progress.setRange(0, len(targets))
        self.fill_btn.setEnabled(False)
        self.fill_cancel_btn.setEnabled(True)
        self._fill_worker = FillDbWorker(targets, pump=True)
        self._fill_worker.progress.connect(self._on_fill_progress)
        self._fill_worker.finished_ok.connect(self._on_fill_finished)
        self._fill_worker.start()

    def _on_fill_progress(self, done, total, msg):
        self.fill_progress.setRange(0, max(total, 1))
        self.fill_progress.setValue(done)
        self.fill_status.setText(msg)
        self.fill_log.append(msg)

    def _on_fill_finished(self, ok, msg):
        self.fill_progress.setVisible(False)
        self.fill_btn.setEnabled(True)
        self.fill_cancel_btn.setEnabled(False)
        self.fill_status.setText(msg)
        self.fill_log.append(("✅ " if ok else "⚠️ ") + msg)

    def _cancel_fill(self):
        if self._fill_worker:
            self._fill_worker.cancel()
            self.fill_status.setText("Annulation...")

    # ---- ajout de port ----
    def _add_port(self):
        ok, msg = ports_module.add_port(
            self.np_name.text(), self.np_code.text(),
            self.np_lat.text() or None, self.np_lon.text() or None,
            self.np_region.text(), self.np_coast.currentText())
        if ok:
            self.ports = ports_module.load_ports()
            self._fill_port_list(self.ports)
            self.ports_info.setText(f"{len(self.ports)} ports disponibles. {msg}")
            for f in (self.np_name, self.np_code, self.np_lat, self.np_lon, self.np_region):
                f.clear()
            QMessageBox.information(self, "Port ajouté",
                                    msg + "\nRedémarrez pour l'afficher sur la carte.")
        else:
            QMessageBox.warning(self, "Ajout impossible", msg)

    def closeEvent(self, event):
        for wkr in (self._gen_worker, self._fill_worker):
            if wkr and wkr.isRunning():
                wkr.cancel()
                wkr.wait(2000)
        event.accept()


STYLE = """
QMainWindow, QWidget { background: #f6f8fa; font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
QGroupBox { font-weight: 600; border: 1px solid #d0d7de; border-radius: 8px; margin-top: 10px; background: white; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; color: #0d6efd; }
QPushButton { background: #e9ecef; border: 1px solid #ced4da; border-radius: 6px; padding: 7px 12px; }
QPushButton:hover { border-color: #0d6efd; }
QPushButton#primary { background: #0d6efd; color: white; border: none; font-weight: 600; }
QPushButton#primary:hover { background: #0b5ed7; }
QPushButton#primary:disabled { background: #9ec5fe; }
QLineEdit, QSpinBox, QComboBox { border: 1px solid #ced4da; border-radius: 6px; padding: 6px; background: white; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #0d6efd; }
QProgressBar { border: 1px solid #ced4da; border-radius: 6px; text-align: center; background: white; height: 20px; }
QProgressBar::chunk { background: #198754; border-radius: 5px; }
QTextEdit, QListWidget { border: 1px solid #d0d7de; border-radius: 6px; background: white; }
QTabBar::tab { padding: 8px 16px; }
QTabBar::tab:selected { color: #0d6efd; font-weight: 600; }
"""


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    try:
        db.init_database()
    except Exception as e:
        print(f"[WARN] init base: {e}")
    win = BeautifulTides()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
