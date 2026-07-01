"""Carte de selection des ports.

Deux implementations, meme API (signal `portSelected(dict)`, methode
`select_code(code)`) :
  - LeafletMap  : carte interactive en ligne (QWebEngine + OpenStreetMap).
  - OfflineMap  : carte hexagone dessinee localement (aucun reseau requis).

`create_port_map(ports)` renvoie la meilleure disponible (Leaflet si le module
QWebEngine est present, sinon la carte hors-ligne).
"""
import json
import math
import os

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QObject, pyqtSlot, QPointF
from PyQt6.QtGui import QPainter, QColor, QPolygonF, QPen, QBrush, QFont

_HERE = os.path.dirname(os.path.abspath(__file__))

# Contour tres simplifie de la France metropolitaine (lon, lat), sens horaire.
FRANCE_OUTLINE = [
    (2.5, 51.0), (7.6, 49.0), (7.6, 47.6), (6.9, 47.5), (6.0, 46.3),
    (7.0, 45.9), (7.0, 45.0), (6.9, 44.1), (7.5, 43.8), (6.0, 43.1),
    (4.8, 43.35), (3.0, 43.2), (3.05, 42.5), (0.7, 42.7), (-1.4, 43.3),
    (-1.25, 44.5), (-1.15, 45.6), (-1.05, 46.2), (-2.2, 47.0), (-2.55, 47.3),
    (-4.8, 48.0), (-4.3, 48.7), (-2.0, 48.6), (-1.6, 49.7), (0.1, 49.5),
    (1.6, 50.1), (2.5, 51.0),
]
LON_MIN, LON_MAX = -5.2, 8.6
LAT_MIN, LAT_MAX = 41.2, 51.4


class OfflineMap(QWidget):
    """Carte dessinee (hors-ligne) : hexagone + pastilles cliquables."""
    portSelected = pyqtSignal(dict)

    def __init__(self, ports, parent=None):
        super().__init__(parent)
        self.ports = [p for p in ports if p.get("lat") is not None and p.get("lon") is not None]
        self.selected_code = None
        self.setMinimumSize(360, 460)
        self.setMouseTracking(True)

    # --- projection lon/lat -> pixels (equirectangulaire corrigee) ---
    def _project(self, lon, lat):
        w, h = self.width(), self.height()
        margin = 16
        cos_lat = math.cos(math.radians((LAT_MIN + LAT_MAX) / 2))
        gx0, gx1 = LON_MIN * cos_lat, LON_MAX * cos_lat
        span_x, span_y = gx1 - gx0, LAT_MAX - LAT_MIN
        avail_w, avail_h = w - 2 * margin, h - 2 * margin
        scale = min(avail_w / span_x, avail_h / span_y)
        off_x = margin + (avail_w - span_x * scale) / 2
        off_y = margin + (avail_h - span_y * scale) / 2
        x = off_x + (lon * cos_lat - gx0) * scale
        y = off_y + (LAT_MAX - lat) * scale
        return QPointF(x, y)

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        qp.fillRect(self.rect(), QColor("#cfe6f2"))  # mer

        # Terre
        poly = QPolygonF([self._project(lon, lat) for lon, lat in FRANCE_OUTLINE])
        qp.setBrush(QBrush(QColor("#eef3e2")))
        qp.setPen(QPen(QColor("#9bbf8f"), 1.5))
        qp.drawPolygon(poly)

        # Titre
        qp.setPen(QColor("#6c757d"))
        qp.setFont(QFont("Arial", 9))
        qp.drawText(12, 18, "Carte hors-ligne")

        # Ports
        for p in self.ports:
            pt = self._project(p["lon"], p["lat"])
            is_sel = str(p["code"]) == str(self.selected_code)
            r = 7 if is_sel else 4
            qp.setBrush(QBrush(QColor("#dc3545") if is_sel else QColor("#0d6efd")))
            qp.setPen(QPen(QColor("white"), 2))
            qp.drawEllipse(pt, r, r)
            if is_sel:
                qp.setPen(QColor("#212529"))
                qp.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                qp.drawText(QPointF(pt.x() + 9, pt.y() + 3), p["name"])
        qp.end()

    def _nearest(self, pos, max_dist=14):
        best, best_d = None, max_dist
        for p in self.ports:
            pt = self._project(p["lon"], p["lat"])
            d = math.hypot(pt.x() - pos.x(), pt.y() - pos.y())
            if d < best_d:
                best, best_d = p, d
        return best

    def mousePressEvent(self, event):
        p = self._nearest(event.position())
        if p:
            self.selected_code = str(p["code"])
            self.update()
            self.portSelected.emit(p)

    def mouseMoveEvent(self, event):
        p = self._nearest(event.position())
        self.setToolTip(p["name"] if p else "")
        self.setCursor(Qt.CursorShape.PointingHandCursor if p else Qt.CursorShape.ArrowCursor)

    def select_code(self, code):
        self.selected_code = str(code)
        self.update()


class _Bridge(QObject):
    """Pont JS -> Python pour la carte Leaflet."""
    clicked = pyqtSignal(str)

    @pyqtSlot(str)
    def portClicked(self, code):
        self.clicked.emit(code)


def _make_leaflet(ports):
    """Retourne un QWidget Leaflet, ou None si QWebEngine indisponible."""
    try:
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebChannel import QWebChannel
        from PyQt6.QtCore import QUrl
    except Exception:
        return None

    class LeafletMap(QWebEngineView):
        portSelected = pyqtSignal(dict)

        def __init__(self, ports, parent=None):
            super().__init__(parent)
            self._ports = {str(p["code"]): p for p in ports}
            self.setMinimumSize(360, 460)
            self._bridge = _Bridge()
            self._bridge.clicked.connect(self._on_clicked)
            self._channel = QWebChannel()
            self._channel.registerObject("bridge", self._bridge)
            self.page().setWebChannel(self._channel)

            html = open(os.path.join(_HERE, "leaflet.html"), encoding="utf-8").read()
            payload = json.dumps([
                {"name": p["name"], "code": str(p["code"]),
                 "lat": p.get("lat"), "lon": p.get("lon")} for p in ports
            ])
            html = html.replace("__PORTS_JSON__", payload)
            # baseUrl https requis pour charger les tuiles/JS Leaflet et qwebchannel.
            self.setHtml(html, QUrl("https://marine.meteoconsult.fr/"))

        def _on_clicked(self, code):
            p = self._ports.get(str(code))
            if p:
                self.portSelected.emit(p)

        def select_code(self, code):
            self.page().runJavaScript(
                f"window.selectPortFromPython && window.selectPortFromPython('{code}');")

    return LeafletMap(ports)


def create_port_map(ports):
    """Renvoie (widget, is_online). Leaflet si possible, sinon carte hors-ligne."""
    try:
        leaflet = _make_leaflet(ports)
    except Exception:
        leaflet = None
    if leaflet is not None:
        return leaflet, True
    return OfflineMap(ports), False
