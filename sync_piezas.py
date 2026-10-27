#!/usr/bin/env python3
"""Copia al panel público las piezas aprobadas del Panel de Claude.

Uso: python3 sync_piezas.py <piezas.json del Panel de Claude> <carpeta con imágenes>

- <piezas.json>: el archivo del dataset "piezas" del Panel de Claude (lista de piezas).
- <carpeta>: imágenes descargadas del Panel, nombradas <id del blob>.<ext>
  (el id del blob es lo que va después de /_blob/ en el campo "imagen").

Escribe data/piezas.json (solo piezas con estado "aprobada") y copia cada imagen a
piezas/<id de la pieza>.<ext>. Imprime "OK n piezas" o termina con error si falta una imagen.
"""
import json
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
CAMPOS = ("id", "fecha", "hora", "red", "formato", "titulo", "copy")


def main(src, img_dir):
    piezas = json.loads(Path(src).read_text(encoding="utf-8"))
    if isinstance(piezas, dict):
        piezas = piezas.get("rows") or piezas.get("data") or piezas.get("results") or []
    img_dir = Path(img_dir)
    (BASE / "piezas").mkdir(exist_ok=True)
    out = []
    for p in piezas:
        if p.get("estado") != "aprobada" or not p.get("fecha"):
            continue
        q = {k: p[k] for k in CAMPOS if p.get(k)}
        img = p.get("imagen") or ""
        if img.startswith("/_blob/"):
            bid = img.rsplit("/", 1)[-1]
            found = sorted(img_dir.glob(bid + ".*"))
            if not found:
                raise SystemExit(f"Falta la imagen {bid} de la pieza {p.get('id')}")
            dest = BASE / "piezas" / (p["id"] + found[0].suffix)
            shutil.copy(found[0], dest)
            q["imagen"] = "piezas/" + dest.name
        elif img:
            q["imagen"] = img
        out.append(q)
    out.sort(key=lambda x: (x["fecha"], x.get("hora", "")))
    (BASE / "data" / "piezas.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"OK {len(out)} piezas")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
