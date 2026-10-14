#!/usr/bin/env python3
"""Prepara il sito per la pubblicazione.

Copia i file del sito in una cartella di uscita e, per ogni lavoro elencato
in lavori.txt, crea:
  - og/<codice>.jpg   immagine di anteprima 1200x630 (quella che WhatsApp mostra)
  - p/<codice>.html   piccola pagina con i dati per l'anteprima, che rimanda al sito

Il <codice> e' il nome della prima foto del lavoro, senza estensione.
Questo script lo esegue GitHub da solo a ogni modifica: non serve lanciarlo a mano.
"""
import argparse
import html
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps

FONDO = (243, 220, 228)          # rosa chiaro del sito
LARGH, ALT = 1200, 630           # formato standard delle anteprime dei link
COPIA = ["index.html", "lavori.txt", "foto", "licenze-caratteri"]


def codice(nome_foto: str) -> str:
    base = re.sub(r"\.[^.]+$", "", nome_foto).lower()
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-")


def leggi_lavori(testo: str):
    lavori = []
    for riga in testo.splitlines():
        riga = riga.strip()
        if not riga or riga.startswith("#"):
            continue
        parti = [p.strip() for p in riga.split("|")]
        nome = parti[0] if parti else ""
        cat = parti[1] if len(parti) > 1 and parti[1] else "Altro"
        foto = [f.strip() for f in (parti[2] if len(parti) > 2 else "").split(",") if f.strip()]
        if nome and foto:
            lavori.append({"nome": nome, "cat": cat, "foto": foto})
    return lavori


def anteprima(src: Path, dst: Path):
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGBA")
    im.thumbnail((LARGH - 120, ALT - 80))
    tela = Image.new("RGB", (LARGH, ALT), FONDO)
    tela.paste(im, ((LARGH - im.width) // 2, (ALT - im.height) // 2), im)
    tela.save(dst, "JPEG", quality=82, optimize=True, progressive=True)


PAGINA = """<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titolo}</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Il Filo di Tamara">
<meta property="og:title" content="{titolo}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
<meta http-equiv="refresh" content="0; url={sito}#{cod}">
<link rel="canonical" href="{sito}#{cod}">
<style>body{{margin:0;font-family:system-ui,sans-serif;background:#F7F2F1;color:#2E2430;display:grid;place-items:center;min-height:100vh;padding:16px;text-align:center}}img{{max-width:100%;border-radius:12px}}a{{color:#A8436A}}</style>
</head>
<body>
<div><img src="{img}" alt="{nome}"><p>{nome}</p><p><a href="{sito}#{cod}">Vai al sito Il Filo di Tamara</a></p></div>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="indirizzo del sito, es. https://utente.github.io/tamara")
    ap.add_argument("--out", default="_site")
    ap.add_argument("--src", default=".")
    a = ap.parse_args()

    src, out = Path(a.src), Path(a.out)
    sito = a.base.rstrip("/") + "/"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for nome in COPIA:
        p = src / nome
        if p.is_dir():
            shutil.copytree(p, out / nome)
        elif p.exists():
            shutil.copy2(p, out / nome)

    (out / "og").mkdir()
    (out / "p").mkdir()
    lavori = leggi_lavori((src / "lavori.txt").read_text(encoding="utf-8"))
    fatti = 0
    for l in lavori:
        foto = src / "foto" / l["foto"][0]
        if not foto.exists():
            print(f"ATTENZIONE: manca la foto {foto.name} per '{l['nome']}', salto l'anteprima", file=sys.stderr)
            continue
        cod = codice(l["foto"][0])
        anteprima(foto, out / "og" / f"{cod}.jpg")
        e = html.escape
        (out / "p" / f"{cod}.html").write_text(PAGINA.format(
            titolo=e(f"{l['nome']} · Il Filo di Tamara"),
            desc=e("Fatto a mano all'uncinetto da Tamara."),
            img=e(f"{sito}og/{cod}.jpg"), url=e(f"{sito}p/{cod}.html"),
            sito=e(sito), cod=cod, nome=e(l["nome"])), encoding="utf-8")
        fatti += 1
    print(f"Anteprime create: {fatti} su {len(lavori)} lavori")


if __name__ == "__main__":
    main()
