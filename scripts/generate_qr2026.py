from pathlib import Path
from io import BytesIO
import re
import sys

import segno
from PIL import Image


# ------------------------------------------------------------
# KONFIGURACE
# ------------------------------------------------------------

# Cesta ke zdrojovému Markdown souboru v repozitáři.
# Může být kdekoliv, například:
#   Path("docs/fotokniha.md")
#   Path("book/fotokniha.md")
#   Path("some/other/dir/fotokniha.md")
SOURCE_MD = Path("2026-calendar.cz.md")

# Veřejná URL stránky, na kterou mají QR kódy odkazovat.
# Musí to být URL bez koncového #anchor.
# Příklady:
#   "https://username.github.io/fotokniha/"
#   "https://username.github.io/book/fotokniha.html"
PAGE_URL = "https://pepcape.github.io/2026-calendar.cz"

# Kam ukládat vygenerované PNG soubory.
OUTPUT_DIR = Path("cal26/qr")

# Výsledná velikost PNG souboru v pixelech.
IMAGE_SIZE = 256

# Šířka tiché zóny (quiet zone) v modulech QR kódu.
BORDER = 4

# Jak mají vypadat platné identifikátory sekcí.
# Pro tvoje kotvy "01", "02", ..., "54" ponech takto:
SECTION_ID_RE = re.compile(r"\d{2}")

# Najde kotvy ve tvaru:
#   <a name="01"></a>
#   <a id="01"></a>
ANCHOR_RE = re.compile(
    r'<a\b[^>]*\b(?:name|id)\s*=\s*["\']([A-Za-z0-9_-]+)["\'][^>]*>\s*</a>',
    re.IGNORECASE
)


# ------------------------------------------------------------
# IMPLEMENTACE
# ------------------------------------------------------------

def extract_sections(markdown_text: str) -> list[str]:
    """
    Najde všechny kotvy <a name="..."></a> nebo <a id="..."></a>,
    vyfiltruje jen platné identifikátory a odstraní duplicity
    při zachování pořadí prvního výskytu.
    """
    found = []
    for match in ANCHOR_RE.finditer(markdown_text):
        section_id = match.group(1)
        if SECTION_ID_RE.fullmatch(section_id):
            found.append(section_id)

    # odstranění duplicit při zachování pořadí
    unique = list(dict.fromkeys(found))
    return unique


def generate_qr_png(url: str, output_file: Path) -> None:
    """
    Vygeneruje QR kód pro dané URL jako PNG 256x256 px
    (nebo obecně IMAGE_SIZE x IMAGE_SIZE) s ostrými hranami.
    """
    qr = segno.make(url, error="m")

    # velikost QR symbolu v modulech (včetně borderu)
    width_modules, height_modules = qr.symbol_size(scale=1, border=BORDER)

    # celočíselná velikost jednoho modulu v pixelech
    scale = IMAGE_SIZE // max(width_modules, height_modules)

    if scale < 1:
        raise ValueError(
            f"QR kód pro URL '{url}' je příliš velký pro plátno "
            f"{IMAGE_SIZE}x{IMAGE_SIZE} px."
        )

    # nejprve vygenerujeme samotný QR do paměti
    buffer = BytesIO()
    qr.save(
        buffer,
        kind="png",
        scale=scale,
        border=BORDER,
        dark="black",
        light="white",
    )
    buffer.seek(0)

    qr_image = Image.open(buffer).convert("RGB")

    # a vložíme ho doprostřed pevného plátna 256x256
    canvas = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), "white")

    x = (IMAGE_SIZE - qr_image.width) // 2
    y = (IMAGE_SIZE - qr_image.height) // 2

    canvas.paste(qr_image, (x, y))
    canvas.save(output_file, "PNG")


def main() -> int:
    if not SOURCE_MD.is_file():
        print(f"ERROR: Zdrojový Markdown soubor neexistuje: {SOURCE_MD}", file=sys.stderr)
        return 1

    markdown_text = SOURCE_MD.read_text(encoding="utf-8")
    sections = extract_sections(markdown_text)

    if not sections:
        print(
            f"ERROR: V souboru {SOURCE_MD} nebyly nalezeny žádné platné kotvy.",
            file=sys.stderr
        )
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # smažeme staré PNG soubory, aby nezůstávaly QR kódy
    # pro sekce, které už v Markdownu nejsou
    for png_file in OUTPUT_DIR.glob("*.png"):
        png_file.unlink()

    print(f"Zdrojový Markdown: {SOURCE_MD}")
    print(f"Cílová URL stránky: {PAGE_URL}")
    print(f"Výstupní adresář:   {OUTPUT_DIR}")
    print(f"Nalezené sekce:     {', '.join(sections)}")
    print()

    for section_id in sections:
        url = f"{PAGE_URL}#{section_id}"
        output_file = OUTPUT_DIR / f"{section_id}.png"
        generate_qr_png(url, output_file)
        print(f"OK  {output_file}  <-  {url}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
