#!/usr/bin/env python3
"""Prepara il sito per la pubblicazione.

Copia i file del sito in una cartella di uscita e, per ogni lavoro elencato
in lavori.txt, crea:
  - og/<codice>.jpg   immagine di anteprima 1200x630 (quella che WhatsApp mostra)
  - p/<codice>.html   piccola pagina con i dati per l'anteprima, che rimanda al sito
Crea anche l'anteprima della pagina principale (og/sito.jpg: nome del sito e le
prime borse della galleria) e ne scrive i dati dentro index.html.

Il <codice> e' il nome della prima foto del lavoro (i video si saltano), senza estensione.
Questo script lo esegue GitHub da solo a ogni modifica: non serve lanciarlo a mano.
"""
import argparse
import base64
import hashlib
import html
import io
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

FONDO = (243, 220, 228)          # rosa chiaro del sito
ACCENTO = (168, 67, 106)         # colore del titolo sul sito
GRIGIO = (125, 111, 120)
DESC_SITO = "Borse, pochette e cestini all'uncinetto, fatti a mano da Tamara."
LARGH, ALT = 1200, 630           # formato standard delle anteprime dei link
COPIA = ["index.html", "lavori.txt", "foto", "licenze-caratteri"]
VIDEO = (".mp4", ".webm", ".mov")


def copertina(lavoro):
    """La prima foto del lavoro: un video non puo' fare da copertina."""
    return next((f for f in lavoro["foto"] if not f.lower().endswith(VIDEO)), None)


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


def versiona(testo: str, cartella: Path) -> str:
    """Aggiunge ?v=<impronta del file> ai nomi delle foto in lavori.txt.

    Se una foto viene sostituita tenendo lo stesso nome, cambia l'impronta e quindi
    l'indirizzo: il browser la riscarica invece di mostrare quella vecchia in memoria.
    I video restano senza: le pagine rimaste in memoria nei browser riconoscono un
    video solo se il nome finisce con .mp4 (o .webm, .mov).
    """
    righe = []
    for riga in testo.splitlines():
        if riga.strip() and not riga.strip().startswith("#") and riga.count("|") >= 2:
            parti = riga.split("|")
            nomi = [n.strip() for n in parti[2].split(",") if n.strip()]
            parti[2] = " " + ", ".join(
                f"{n}?v={hashlib.sha1((cartella / n).read_bytes()).hexdigest()[:10]}" if (cartella / n).is_file() and not n.lower().endswith(VIDEO) else n
                for n in nomi)
            riga = "|".join(parti)
        righe.append(riga)
    return "\n".join(righe) + "\n"


def anteprima(src: Path, dst: Path):
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGBA")
    im.thumbnail((LARGH - 120, ALT - 80))
    tela = Image.new("RGB", (LARGH, ALT), FONDO)
    tela.paste(im, ((LARGH - im.width) // 2, (ALT - im.height) // 2), im)
    tela.save(dst, "JPEG", quality=82, optimize=True, progressive=True)


def carattere(testo_html: str, nome: str, grandezza: int):
    """Il carattere incorporato in index.html (Cookie o Nunito); None se non si riesce a leggerlo."""
    m = re.search(r'font-family:"%s";src:url\(data:font/woff;base64,([A-Za-z0-9+/=]+)\)' % nome, testo_html)
    try:
        return ImageFont.truetype(io.BytesIO(base64.b64decode(m.group(1))), grandezza)
    except Exception:
        return None


def anteprima_sito(foto, dst: Path, testo_html: str):
    """Anteprima della pagina principale: il nome del sito e le prime borse della galleria."""
    tela = Image.new("RGBA", (LARGH, ALT), FONDO + (255,))
    d = ImageDraw.Draw(tela)
    titolo, sotto = carattere(testo_html, "Cookie", 116), carattere(testo_html, "Nunito", 24)
    if titolo:
        d.text((LARGH // 2, 88), "Il Filo di Tamara", font=titolo, fill=ACCENTO, anchor="mm")
    if sotto:
        d.text((LARGH // 2, 158), "UNCINETTO FATTO A MANO", font=sotto, fill=GRIGIO, anchor="mm")
    cella, alto, cima = (LARGH - 40) // len(foto), ALT - 225, 192
    for i, f in enumerate(foto):
        im = ImageOps.exif_transpose(Image.open(f)).convert("RGBA")
        im.thumbnail((cella - 40, alto))
        x, y = 20 + i * cella + (cella - im.width) // 2, cima + (alto - im.height) // 2
        ombra = Image.new("RGBA", im.size, (60, 20, 40, 0))
        ombra.putalpha(im.getchannel("A").point(lambda v: v * 55 // 255))
        tela.alpha_composite(ombra.filter(ImageFilter.GaussianBlur(9)), (x, min(y + 10, ALT - im.height)))
        tela.alpha_composite(im, (x, y))
    tela.convert("RGB").save(dst, "JPEG", quality=84, optimize=True, progressive=True)


META_SITO = """<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Il Filo di Tamara">
<meta property="og:title" content="Il Filo di Tamara · uncinetto fatto a mano">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
"""


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
    (out / "lavori.txt").write_text(versiona((src / "lavori.txt").read_text(encoding="utf-8"), src / "foto"), encoding="utf-8")

    (out / "og").mkdir()
    (out / "p").mkdir()
    lavori = leggi_lavori((src / "lavori.txt").read_text(encoding="utf-8"))
    fatti = 0
    for l in lavori:
        cop = copertina(l)
        if cop is None:
            print(f"ATTENZIONE: '{l['nome']}' ha solo video e nessuna foto di copertina, non compare sul sito", file=sys.stderr)
            continue
        foto = src / "foto" / cop
        if not foto.exists():
            print(f"ATTENZIONE: manca la foto {foto.name} per '{l['nome']}', salto l'anteprima", file=sys.stderr)
            continue
        cod = codice(cop)
        anteprima(foto, out / "og" / f"{cod}.jpg")
        e = html.escape
        (out / "p" / f"{cod}.html").write_text(PAGINA.format(
            titolo=e(f"{l['nome']} · Il Filo di Tamara"),
            desc=e("Fatto a mano all'uncinetto da Tamara."),
            img=e(f"{sito}og/{cod}.jpg"), url=e(f"{sito}p/{cod}.html"),
            sito=e(sito), cod=cod, nome=e(l["nome"])), encoding="utf-8")
        fatti += 1
    print(f"Anteprime create: {fatti} su {len(lavori)} lavori")

    # pagina principale: anteprima con le prime 3 borse dell'elenco e dati per WhatsApp/Facebook
    testo_html = (out / "index.html").read_text(encoding="utf-8")
    prime = [src / "foto" / copertina(l) for l in lavori if copertina(l) and (src / "foto" / copertina(l)).exists()][:3]
    img = ""
    if prime:
        anteprima_sito(prime, out / "og" / "sito.jpg", testo_html)
        img = f"{sito}og/sito.jpg?v={hashlib.sha1((out / 'og' / 'sito.jpg').read_bytes()).hexdigest()[:10]}"
    meta = META_SITO.format(desc=html.escape(DESC_SITO), img=html.escape(img), url=html.escape(sito))
    (out / "index.html").write_text(testo_html.replace("</head>", meta + "</head>", 1), encoding="utf-8")
    print(f"Anteprima della pagina principale: {len(prime)} borse")


if __name__ == "__main__":
    main()
