#!/usr/bin/env python3
"""Génère les icônes de l'application (PNG) sans dépendance externe.

Usage : python tools/generer_icones.py
Écrit dans adherents/static/icons/. Pour utiliser votre propre logo, remplacez
simplement les 4 fichiers PNG (192, 512, maskable 512, apple-touch 180).
"""
import math
import os
import struct
import zlib

FOND = (0x7A, 0x5C, 0x00)
MIEL = (0xE8, 0xB4, 0x00)
SORTIE = os.path.join(os.path.dirname(__file__), "..", "adherents", "static", "icons")
SURECHANTILLONNAGE = 3


def dans_hexagone(x, y, rayon):
    """Hexagone régulier, sommet en haut, centré à l'origine."""
    x, y = abs(x), abs(y)
    a = rayon * math.sqrt(3) / 2
    return x <= a and y <= rayon - x / math.sqrt(3)


def couleur_en(x, y, taille, echelle):
    """Couleur du point (x, y) en coordonnées relatives au centre."""
    rayon = taille * echelle
    if dans_hexagone(x, y, rayon):
        if x * x + y * y <= (rayon * 0.34) ** 2:  # trou central : repère de carte
            return FOND
        return MIEL
    return FOND


def png(chemin, taille, echelle):
    lignes = []
    n = SURECHANTILLONNAGE
    centre = taille / 2
    for j in range(taille):
        ligne = bytearray([0])  # filtre PNG « aucun »
        for i in range(taille):
            r = g = b = 0
            for dj in range(n):
                for di in range(n):
                    x = i + (di + 0.5) / n - centre
                    y = j + (dj + 0.5) / n - centre
                    c = couleur_en(x, y, taille, echelle)
                    r += c[0]
                    g += c[1]
                    b += c[2]
            k = n * n
            ligne += bytes((r // k, g // k, b // k))
        lignes.append(bytes(ligne))

    def bloc(nom, donnees):
        return (
            struct.pack(">I", len(donnees)) + nom + donnees
            + struct.pack(">I", zlib.crc32(nom + donnees) & 0xFFFFFFFF)
        )

    contenu = (
        b"\x89PNG\r\n\x1a\n"
        + bloc(b"IHDR", struct.pack(">IIBBBBB", taille, taille, 8, 2, 0, 0, 0))
        + bloc(b"IDAT", zlib.compress(b"".join(lignes), 9))
        + bloc(b"IEND", b"")
    )
    with open(chemin, "wb") as f:
        f.write(contenu)
    print("écrit :", os.path.normpath(chemin))


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    png(os.path.join(SORTIE, "icone-192.png"), 192, 0.40)
    png(os.path.join(SORTIE, "icone-512.png"), 512, 0.40)
    # « maskable » : le motif reste dans la zone sûre (80 % centraux)
    png(os.path.join(SORTIE, "icone-maskable-512.png"), 512, 0.30)
    png(os.path.join(SORTIE, "apple-touch-icon.png"), 180, 0.40)
