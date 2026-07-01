"""Galerie de fonds avec apercu visuel (remplace le menu de numeros).

Affiche une vignette de chaque fond (via backgrounds.preview_image) dans une
grille cliquable. Selection simple ou multiple ; emet `selectionChanged`.
"""
from PyQt6.QtWidgets import (QWidget, QGridLayout, QVBoxLayout, QLabel, QFrame,
                             QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap

import backgrounds

THUMB_W, THUMB_H = 168, 100


def _pil_to_pixmap(pil_img):
    pil_img = pil_img.convert("RGB")
    data = pil_img.tobytes("raw", "RGB")
    qimg = QImage(data, pil_img.width, pil_img.height, pil_img.width * 3,
                  QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())


class _FondTile(QFrame):
    clicked = pyqtSignal(str, object)  # (fond_id, modifiers)

    def __init__(self, meta, pixmap):
        super().__init__()
        self.fond_id = meta["id"]
        self.setObjectName("fondTile")
        self.setFixedWidth(THUMB_W + 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._selected = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)

        img = QLabel()
        img.setPixmap(pixmap)
        img.setFixedSize(THUMB_W, THUMB_H)
        img.setScaledContents(True)
        img.setStyleSheet("border-radius: 6px;")
        lay.addWidget(img, alignment=Qt.AlignmentFlag.AlignCenter)

        name = QLabel(meta["name"])
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setWordWrap(True)
        name.setStyleSheet("font-size: 11px; color: #333;")
        lay.addWidget(name)

        self._apply_style()

    def set_selected(self, value):
        self._selected = value
        self._apply_style()

    def _apply_style(self):
        if self._selected:
            self.setStyleSheet("#fondTile { border: 3px solid #0d6efd; border-radius: 8px;"
                               " background: #e7f1ff; }")
        else:
            self.setStyleSheet("#fondTile { border: 1px solid #ced4da; border-radius: 8px;"
                               " background: white; } #fondTile:hover { border-color: #0d6efd; }")

    def mousePressEvent(self, event):
        self.clicked.emit(self.fond_id, event.modifiers())


class FondGallery(QScrollArea):
    """Grille de fonds. `multi=True` autorise la selection multiple."""
    selectionChanged = pyqtSignal(list)

    def __init__(self, multi=True, columns=4, parent=None):
        super().__init__(parent)
        self.multi = multi
        self.columns = columns
        self._selected = []
        self._tiles = {}

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        self.grid = QGridLayout(container)
        self.grid.setSpacing(10)
        self.grid.setContentsMargins(6, 6, 6, 6)
        self.setWidget(container)

        self._build_tiles()

    def _build_tiles(self):
        for i, meta in enumerate(backgrounds.FONDS):
            pix = _pil_to_pixmap(backgrounds.preview_image(meta["id"], THUMB_W, THUMB_H))
            tile = _FondTile(meta, pix)
            tile.clicked.connect(self._on_tile_clicked)
            r, c = divmod(i, self.columns)
            self.grid.addWidget(tile, r, c)
            self._tiles[meta["id"]] = tile

    def _on_tile_clicked(self, fond_id, modifiers):
        if self.multi:
            ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier) or \
                   bool(modifiers & Qt.KeyboardModifier.MetaModifier)
            if fond_id in self._selected:
                if ctrl or len(self._selected) > 1:
                    self._selected.remove(fond_id)
            else:
                if ctrl:
                    self._selected.append(fond_id)
                else:
                    self._selected = [fond_id]
        else:
            self._selected = [fond_id]
        self._refresh()

    def _refresh(self):
        for fid, tile in self._tiles.items():
            tile.set_selected(fid in self._selected)
        self.selectionChanged.emit(list(self._selected))

    def set_selected(self, ids):
        valid = [i for i in ids if i in self._tiles]
        self._selected = valid if self.multi else valid[:1]
        self._refresh()

    def selected_ids(self):
        return list(self._selected)

    def sizeHint(self):
        return QSize((THUMB_W + 26) * self.columns + 30, 340)
