"""Registre des fonds (arriere-plans) de Beautiful Tides.

Chaque fond est identifie par un `id` (chaine). Les fonds 1-8 reproduisent
EXACTEMENT le comportement pixel de l'ancien `creee_image_fond` : leur code
est deplace ici a l'identique (verifie par tests/pixel_baseline.py).

Les fonds >= 9 sont de nouveaux styles, tous deterministes (seeded) pour etre
reproductibles.

API :
    FONDS                 -> liste ordonnee de metadonnees {id, name, description, category}
    fond_ids()            -> liste des ids ("1", "2", ...)
    generate_fond(fid, height, width, size_factor, out_path)
                          -> ecrit l'image de fond sur disque (BGR/PNG) ; utilise
                             par le pipeline de rendu.
    preview_image(fid, width, height) -> PIL.Image (RGB) pour la galerie de l'UI.
"""
import os
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

DEFAULT_COLORS_PATH = os.path.join("ressources", "colors.png")

# Metadonnees affichees dans l'UI. L'ordre definit l'ordre de la galerie.
FONDS = [
    {"id": "1", "name": "Vagues zigzag", "description": "Zigzags pastel facon vagues", "category": "Texture"},
    {"id": "2", "name": "Bulles bleues", "description": "Cercles bleus flous", "category": "Texture"},
    {"id": "3", "name": "Sable uni", "description": "Aplat sable/kaki doux", "category": "Uni"},
    {"id": "4", "name": "Bleu ciel uni", "description": "Aplat bleu clair", "category": "Uni"},
    {"id": "5", "name": "Kaki uni", "description": "Aplat vert-gris", "category": "Uni"},
    {"id": "6", "name": "Bleu profond uni", "description": "Aplat bleu soutenu", "category": "Uni"},
    {"id": "7", "name": "Bandes marines", "description": "Sable / bleu / kaki", "category": "Bandes"},
    {"id": "8", "name": "Bandes vives", "description": "Vert / rose / bleu vif", "category": "Bandes"},
    # --- Nouveaux fonds (deterministes) ---
    {"id": "9", "name": "Degrade sable-mer", "description": "Degrade vertical sable vers mer", "category": "Degrade"},
    {"id": "10", "name": "Degrade coucher", "description": "Degrade diagonal coucher de soleil", "category": "Degrade"},
    {"id": "11", "name": "Degrade lagon", "description": "Degrade vertical turquoise", "category": "Degrade"},
    {"id": "12", "name": "Quatre bandes", "description": "Quatre bandes cotieres", "category": "Bandes"},
    {"id": "13", "name": "Bandes diagonales", "description": "Bandes obliques bleu/sable", "category": "Bandes"},
    {"id": "14", "name": "Vagues sinus", "description": "Rayures sinusoidales douces (seeded)", "category": "Texture"},
    {"id": "15", "name": "Bulles pastel", "description": "Champ de bulles pastel (seeded)", "category": "Texture"},
    {"id": "16", "name": "Ardoise unie", "description": "Aplat gris-bleu elegant", "category": "Uni"},
    {"id": "17", "name": "Terracotta uni", "description": "Aplat terracotta doux", "category": "Uni"},
]


def fond_ids():
    return [f["id"] for f in FONDS]


def fond_meta(fid):
    for f in FONDS:
        if f["id"] == str(fid):
            return f
    return None


# ---------------------------------------------------------------------------
# Rendu exact utilise par le pipeline (ecrit ressources/colors.png)
# Les branches 1-8 sont copiees a l'identique de l'ancien creee_image_fond.
# ---------------------------------------------------------------------------
def generate_fond(fid, height, width, size_factor, out_path=DEFAULT_COLORS_PATH):
    """Genere l'image de fond plein format et l'ecrit sur disque.

    Reproduit exactement l'ancien `creee_image_fond` pour les fonds 1-8.
    """
    fid = str(fid)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    if fid == "1":
        background_color = (255, 255, 255)
        pastel_colors = [(100, 200, 200), (150, 200, 200), (120, 180, 180), (95, 200, 200), (170, 210, 210)]
        for i in range(len(pastel_colors)):
            pastel_colors[i] = (pastel_colors[i][2], pastel_colors[i][1], pastel_colors[i][0])
        colors = [tuple(np.array(c) / 255.0) for c in pastel_colors]

        image = np.ones((height, width, 3), dtype=np.float32) * background_color

        nb_zigzags_per_line = height // (2 * size_factor)
        zigzag_width = width // 9
        zigzag_height = height // nb_zigzags_per_line
        zigzag_thickness = height // (nb_zigzags_per_line)

        for i in range(nb_zigzags_per_line):
            y = i * zigzag_height
            color = colors[i % len(colors)]
            for x in range(0, width, zigzag_width):
                if x % (2 * zigzag_width) == 0:
                    cv2.line(image, (x, y), (x + zigzag_width, y + zigzag_height), color, zigzag_thickness)
                else:
                    cv2.line(image, (x, y + zigzag_height), (x + zigzag_width, y), color, zigzag_thickness)

        image = (image * 255).astype(np.uint8)
        cv2.imwrite(out_path, image)

    elif fid == "2":
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        for _ in range(1000):
            rayon = random.randint(width // 20, width // 10)
            x = random.randint(0, width)
            y = random.randint(0, height)
            couleur_bleu = random.randint(190, 255)
            couleur = (110, 120, couleur_bleu)
            draw.ellipse([x - rayon, y - rayon, x + rayon, y + rayon], fill=couleur)
        image_blurred = image.filter(ImageFilter.GaussianBlur(radius=width // 80))
        image_blurred.save(out_path)

    elif fid == "3":
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[:] = (173, 162, 131)
        cv2.imwrite(out_path, image)

    elif fid == "4":
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[:] = (123, 176, 236)
        cv2.imwrite(out_path, image)

    elif fid == "5":
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[:] = (151, 171, 159)
        cv2.imwrite(out_path, image)

    elif fid == "6":
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[:] = (212, 196, 130)
        cv2.imwrite(out_path, image)

    elif fid == "7":
        top_color = (173, 162, 131)
        middle_color = (123, 176, 236)
        bottom_color = (151, 171, 159)
        hauteur1 = int(height / 2.71)
        hauteur2 = int(1.99 * height / 3)
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[:hauteur1] = top_color
        image[hauteur1:hauteur2] = middle_color
        image[hauteur2:] = bottom_color
        cv2.imwrite(out_path, image)

    elif fid == "8":
        top_color = (167, 176, 118)
        middle_color = (142, 141, 241)
        bottom_color = (99, 164, 244)
        hauteur1 = int(height / 2.567)
        hauteur2 = int(2.009 * height / 3)
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[:hauteur1] = top_color
        image[hauteur1:hauteur2] = middle_color
        image[hauteur2:] = bottom_color
        cv2.imwrite(out_path, image)

    else:
        # Nouveaux fonds : rendus deterministes en BGR.
        image = _render_new_fond_bgr(fid, height, width)
        cv2.imwrite(out_path, image)


# ---------------------------------------------------------------------------
# Nouveaux fonds (>= 9). Couleurs exprimees en RGB puis converties en BGR pour
# rester coherentes avec la convention cv2 utilisee au compositing.
# ---------------------------------------------------------------------------
def _rgb(*c):
    return tuple(c)


def _vertical_gradient_bgr(height, width, top_rgb, bottom_rgb):
    top = np.array(top_rgb, dtype=np.float32)
    bot = np.array(bottom_rgb, dtype=np.float32)
    t = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]  # (H,1)
    col = top[None, :] * (1 - t) + bot[None, :] * t              # (H,3) RGB
    img_rgb = np.repeat(col[:, None, :], width, axis=1)          # (H,W,3)
    img_rgb = img_rgb.astype(np.uint8)
    return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)


def _diagonal_gradient_bgr(height, width, a_rgb, b_rgb):
    a = np.array(a_rgb, dtype=np.float32)
    b = np.array(b_rgb, dtype=np.float32)
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    t = (yy / max(height - 1, 1) + xx / max(width - 1, 1)) / 2.0  # (H,W) in [0,1]
    t = t[:, :, None]
    img_rgb = (a[None, None, :] * (1 - t) + b[None, None, :] * t).astype(np.uint8)
    return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)


def _render_new_fond_bgr(fid, height, width):
    fid = str(fid)
    if fid == "9":   # Degrade sable -> mer
        return _vertical_gradient_bgr(height, width, _rgb(235, 222, 190), _rgb(70, 130, 160))
    if fid == "10":  # Degrade coucher (diagonal)
        return _diagonal_gradient_bgr(height, width, _rgb(255, 209, 148), _rgb(209, 106, 117))
    if fid == "11":  # Degrade lagon
        return _vertical_gradient_bgr(height, width, _rgb(180, 230, 225), _rgb(40, 120, 140))
    if fid == "12":  # Quatre bandes cotieres
        colors_rgb = [_rgb(235, 222, 190), _rgb(150, 200, 200), _rgb(90, 150, 175), _rgb(150, 171, 159)]
        img_rgb = np.zeros((height, width, 3), dtype=np.uint8)
        bounds = [0, int(height * 0.30), int(height * 0.55), int(height * 0.78), height]
        for i in range(4):
            img_rgb[bounds[i]:bounds[i + 1]] = colors_rgb[i]
        return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    if fid == "13":  # Bandes diagonales bleu/sable
        a = np.array(_rgb(120, 170, 200), dtype=np.float32)
        b = np.array(_rgb(235, 222, 190), dtype=np.float32)
        yy, xx = np.mgrid[0:height, 0:width]
        band = ((xx + yy) // max(width // 9, 1)) % 2
        img_rgb = np.where(band[:, :, None] == 0, a[None, None, :], b[None, None, :]).astype(np.uint8)
        return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    if fid == "14":  # Vagues sinusoidales (seeded, deterministe)
        base = _vertical_gradient_bgr(height, width, _rgb(200, 225, 225), _rgb(90, 160, 175))
        base_rgb = cv2.cvtColor(base, cv2.COLOR_BGR2RGB).astype(np.float32)
        yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
        wave = np.sin(xx / max(width / 14.0, 1) + yy / max(height / 6.0, 1))
        shade = (wave[:, :, None] * 14.0)
        img_rgb = np.clip(base_rgb + shade, 0, 255).astype(np.uint8)
        return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    if fid == "15":  # Bulles pastel (seeded, deterministe)
        rng = random.Random(1234)
        image = Image.new("RGB", (width, height), (232, 240, 240))
        draw = ImageDraw.Draw(image)
        palette = [(150, 200, 200), (180, 215, 210), (120, 180, 185), (205, 225, 220)]
        for _ in range(600):
            rayon = rng.randint(width // 22, width // 11)
            x = rng.randint(0, width)
            y = rng.randint(0, height)
            draw.ellipse([x - rayon, y - rayon, x + rayon, y + rayon], fill=rng.choice(palette))
        image = image.filter(ImageFilter.GaussianBlur(radius=max(width // 90, 1)))
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    if fid == "16":  # Ardoise unie
        img_rgb = np.zeros((height, width, 3), dtype=np.uint8)
        img_rgb[:] = _rgb(96, 116, 132)
        return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    if fid == "17":  # Terracotta unie
        img_rgb = np.zeros((height, width, 3), dtype=np.uint8)
        img_rgb[:] = _rgb(202, 128, 100)
        return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    # Repli : blanc
    return np.full((height, width, 3), 255, dtype=np.uint8)


# ---------------------------------------------------------------------------
# Apercu pour la galerie (rapide, en memoire, sans effet de bord disque)
# ---------------------------------------------------------------------------
def preview_image(fid, width=200, height=120):
    """Retourne une PIL.Image RGB representative du fond, pour l'UI."""
    fid = str(fid)
    # size_factor petit et coherent pour l'apercu du zigzag
    sf = max(height // 8, 2)
    if fid in ("2",):
        # rendu aleatoire representatif sans ecrire sur disque
        image = Image.new("RGB", (width, height), "white")
        d = ImageDraw.Draw(image)
        rng = random.Random(7)
        for _ in range(120):
            r = rng.randint(width // 20, width // 10)
            x = rng.randint(0, width)
            y = rng.randint(0, height)
            b = rng.randint(190, 255)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(110, 120, b))
        return image.filter(ImageFilter.GaussianBlur(radius=max(width // 40, 1)))

    # Pour tous les autres, on reutilise le rendu exact a petite echelle en
    # ecrivant dans un fichier temporaire memoire-like puis relecture.
    tmp = os.path.join("ressources", f"_preview_{fid}.png")
    os.makedirs("ressources", exist_ok=True)
    try:
        generate_fond(fid, height, width, sf, out_path=tmp)
        bgr = cv2.imread(tmp)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
