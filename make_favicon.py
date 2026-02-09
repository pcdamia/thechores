#!/usr/bin/env python3
"""Generate favicon.ico and PNG favicons from app icon."""
from pathlib import Path

from PIL import Image

STATIC = Path(__file__).resolve().parent / "app" / "static"
SRC = STATIC / "app-icon.png"
SIZES_ICO = [(16, 16), (32, 32), (48, 48)]
SIZES_PNG = [(16, 16), (32, 32), (180, 180)]  # 180 for apple-touch-icon

def main():
    if not SRC.exists():
        print(f"Source image not found: {SRC}")
        return
    img = Image.open(SRC).convert("RGBA")
    # Favicon.ico with multiple sizes (Pillow uses largest as primary)
    ico_sizes = [img.resize(s, Image.Resampling.LANCZOS) for s in SIZES_ICO]
    ico_path = STATIC / "favicon.ico"
    ico_sizes[-1].save(ico_path, format="ICO", sizes=SIZES_ICO)
    print(f"Wrote {ico_path}")
    # PNG favicons
    for w, h in SIZES_PNG:
        out = STATIC / (f"favicon-{w}x{h}.png" if w != 180 else "apple-touch-icon.png")
        img.resize((w, h), Image.Resampling.LANCZOS).save(out)
        print(f"Wrote {out}")

if __name__ == "__main__":
    main()
