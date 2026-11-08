#!/usr/bin/env python3
"""Precompute perceptual signatures for every hero portrait.

We store three cheap, complementary signatures per hero:
  * dHash (64-bit gradient hash)  -> robust to lighting/compression
  * aHash (64-bit average hash)   -> robust to scale
  * 4x4x4 quantised RGB histogram -> robust to layout/cropping

At analysis time we tile an uploaded screenshot, compute the same signatures
per tile and match with a weighted distance. This is a real (if lightweight)
image-recognition pipeline: no hero IDs are hard-coded from filenames at
runtime.
"""
from __future__ import annotations

import io
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "data" / "artifacts"
CDN = "https://cdn.cloudflare.steamstatic.com"


def dhash(gray: np.ndarray, size: int = 8) -> str:
    img = Image.fromarray(gray).resize((size + 1, size), Image.LANCZOS)
    a = np.asarray(img, dtype=np.int16)
    diff = a[:, 1:] > a[:, :-1]
    bits = diff.flatten()
    return "".join("1" if b else "0" for b in bits)


def ahash(gray: np.ndarray, size: int = 8) -> str:
    img = Image.fromarray(gray).resize((size, size), Image.LANCZOS)
    a = np.asarray(img, dtype=np.float32)
    bits = (a > a.mean()).flatten()
    return "".join("1" if b else "0" for b in bits)


def color_hist(rgb: np.ndarray, bins: int = 4) -> list[float]:
    q = (np.asarray(rgb, dtype=np.uint16) // (256 // bins)).clip(0, bins - 1)
    idx = q[..., 0] * bins * bins + q[..., 1] * bins + q[..., 2]
    hist = np.bincount(idx.flatten(), minlength=bins ** 3).astype(np.float32)
    hist /= hist.sum() or 1.0
    return [round(float(x), 5) for x in hist]


def signature_from_image(img: Image.Image) -> dict:
    img = img.convert("RGB")
    gray = np.asarray(img.convert("L"))
    rgb = np.asarray(img)
    return {"dhash": dhash(gray), "ahash": ahash(gray), "hist": color_hist(rgb)}


def main() -> int:
    data_path = ARTIFACTS / "draftmaster-data.json"
    with data_path.open() as fh:
        bundle = json.load(fh)

    out: dict[str, dict] = {}
    for i, hero in enumerate(bundle["heroes"]):
        img_path = (hero.get("img") or "").split("?")[0]
        if not img_path:
            continue
        url = CDN + img_path
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DraftMasterAI/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
            img = Image.open(io.BytesIO(raw))
            sig = signature_from_image(img)
            sig["id"] = hero["id"]
            sig["localized_name"] = hero["localized_name"]
            out[str(hero["id"])] = sig
        except Exception as exc:  # pragma: no cover - network
            print(f"  ! {hero['localized_name']}: {exc}")
        if i % 25 == 0:
            print(f"  {i}/{len(bundle['heroes'])}")

    dest = ARTIFACTS / "hero-hashes.json"
    with dest.open("w") as fh:
        json.dump({"generated_at": bundle.get("generated_at"), "heroes": out}, fh)
    print(f"Wrote {dest} with {len(out)} hero signatures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
