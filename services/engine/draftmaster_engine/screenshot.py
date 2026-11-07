"""Screenshot analyzer: detect the heroes in an uploaded draft screenshot.

Pipeline
--------
1. Decode the image, downscale, and convert to greyscale/RGB arrays.
2. Segment candidate hero tiles with a grid scan: for each candidate box we
   compute the same dHash/aHash/colour-histogram signatures used for the hero
   portraits (see tools/pipeline/build_hero_hashes.py).
3. Rank matches with a weighted distance and reject anything below a
   confidence floor, then deduplicate.
4. Return detected hero IDs which the API feeds straight into the report
   engine, so the user gets a full win plan from a screenshot alone.

This is deliberately dependency-light (Pillow + numpy) so it runs anywhere,
including on a small Railway container. The scoring is transparent: every
detection carries its own confidence and distance breakdown.
"""
from __future__ import annotations

import io
import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
from PIL import Image

from .dataset import DEFAULT_ARTIFACT

HASH_ARTIFACT = DEFAULT_ARTIFACT.parent / "hero-hashes.json"

# Grid scan configuration. Draft screenshots are usually a row of 5-10 square
# portraits; we scan a generous range of tile sizes.
TILE_SIZES = [48, 56, 64, 72, 80, 96, 112]
# A true portrait match scores ~0.98 with a ~0.30 lead over the runner-up,
# whereas a misaligned crop of the *same* portrait tops out near 0.71 with a
# ~0.03 lead. Both a floor and a margin are therefore required, which is what
# turns "best guess per tile" into a precise detector.
CONFIDENCE_FLOOR = 0.82
CONFIDENCE_MARGIN = 0.08
# Cheap pre-filter used by the coarse scan before local refinement.
COARSE_FLOOR = 0.70
MAX_CANDIDATES = 60


@dataclass
class Detection:
    hero_id: int
    localized_name: str
    confidence: float
    margin: float
    x: int
    y: int
    size: int

    def to_dict(self) -> dict:
        return asdict(self)


class ScreenshotAnalyzer:
    def __init__(self, hashes_path: str | Path | None = None):
        self.hashes_path = Path(hashes_path) if hashes_path else HASH_ARTIFACT
        self.signatures: list[dict] = []
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        with open(self.hashes_path) as fh:
            payload = json.load(fh)
        self.signatures = list(payload["heroes"].values())
        # Pre-vectorise the reference set so matching is a handful of numpy ops
        # instead of a Python loop over every hero for every tile.
        self._ref_dhash = np.array(
            [[int(c) for c in s["dhash"]] for s in self.signatures], dtype=np.int8
        )
        self._ref_ahash = np.array(
            [[int(c) for c in s["ahash"]] for s in self.signatures], dtype=np.int8
        )
        self._ref_hist = np.array([s["hist"] for s in self.signatures], dtype=np.float32)
        self._loaded = True

    # -- signature helpers (mirror the builder exactly) ------------------
    @staticmethod
    def _sig_from_array(rgb: np.ndarray) -> dict:
        img = Image.fromarray(rgb.astype(np.uint8))
        gray = np.asarray(img.convert("L"))
        g_small = Image.fromarray(gray).resize((9, 8), Image.LANCZOS)
        ga = np.asarray(g_small, dtype=np.int16)
        dhash = "".join("1" if b else "0" for b in (ga[:, 1:] > ga[:, :-1]).flatten())
        a_small = Image.fromarray(gray).resize((8, 8), Image.LANCZOS)
        aa = np.asarray(a_small, dtype=np.float32)
        ahash = "".join("1" if b else "0" for b in (aa > aa.mean()).flatten())
        q = (rgb.astype(np.uint16) // 64).clip(0, 3)
        idx = q[..., 0] * 16 + q[..., 1] * 4 + q[..., 2]
        hist = np.bincount(idx.flatten(), minlength=64).astype(np.float32)
        hist /= hist.sum() or 1.0
        return {"dhash": dhash, "ahash": ahash, "hist": hist}

    def _match(self, sig: dict) -> tuple[dict | None, float, float]:
        """Vectorised nearest-neighbour match; returns (ref, confidence, margin)."""
        self._load()
        dhash = np.fromiter((int(c) for c in sig["dhash"]), dtype=np.int8, count=64)
        ahash = np.fromiter((int(c) for c in sig["ahash"]), dtype=np.int8, count=64)
        hist = sig["hist"]
        d = np.abs(self._ref_dhash - dhash).sum(axis=1) / 64.0
        a = np.abs(self._ref_ahash - ahash).sum(axis=1) / 64.0
        h = np.abs(self._ref_hist - hist).sum(axis=1) / 2.0
        conf = 1.0 - (0.30 * d + 0.15 * a + 0.55 * h)
        top = np.argpartition(-conf, 1)[:2]
        top = top[np.argsort(-conf[top])]
        best_idx = int(top[0])
        margin = float(conf[best_idx] - conf[int(top[1])])
        return self.signatures[best_idx], float(conf[best_idx]), margin

    # -- public API ------------------------------------------------------
    def analyse(self, image_bytes: bytes, max_heroes: int = 10) -> dict:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        # Normalise very large screenshots for speed.
        if max(img.size) > 1600:
            ratio = 1600 / max(img.size)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        arr = np.asarray(img)
        height, width = arr.shape[0], arr.shape[1]

        candidates = self._coarse_scan(arr)
        detections = self._refine(arr, candidates, width, height)
        return self._dedupe(detections, max_heroes, img.size)

    def _coarse_scan(self, arr: np.ndarray) -> list[tuple[float, int, int, int]]:
        """Stage 1: cheap half-stride grid scan to locate candidate portraits."""
        height, width = arr.shape[0], arr.shape[1]
        found: list[tuple[float, int, int, int]] = []
        for tile in TILE_SIZES:
            stride = max(8, tile // 2)
            for y in range(0, max(1, height - tile + 1), stride):
                for x in range(0, max(1, width - tile + 1), stride):
                    patch = arr[y : y + tile, x : x + tile]
                    if patch.shape[0] < tile or patch.shape[1] < tile:
                        continue
                    # Skip near-uniform tiles (background) cheaply.
                    if float(patch.std()) < 18.0:
                        continue
                    ref, conf, margin = self._match(self._sig_from_array(patch))
                    if ref and conf >= COARSE_FLOOR:
                        found.append((conf, x, y, tile))
        found.sort(key=lambda row: -row[0])
        return found[:MAX_CANDIDATES]

    def _refine(
        self, arr: np.ndarray, candidates: list[tuple[float, int, int, int]], width: int, height: int
    ) -> list[Detection]:
        """Stage 2: snap each candidate to the exact tile and apply the real gate.

        The coarse scan can be off by up to half a tile, which measurably degrades
        the signature. A local search at pixel resolution recovers the exact crop,
        after which the strict confidence floor and margin are applied.
        """
        detections: list[Detection] = []
        for _, cx, cy, tile in candidates:
            window = tile // 2
            best_conf, best_ref, best_margin, best_pos = 0.0, None, 0.0, (cx, cy)
            for dy in range(-window, window + 1, 2):
                for dx in range(-window, window + 1, 2):
                    nx, ny = cx + dx, cy + dy
                    if nx < 0 or ny < 0 or ny + tile > height or nx + tile > width:
                        continue
                    patch = arr[ny : ny + tile, nx : nx + tile]
                    ref, conf, margin = self._match(self._sig_from_array(patch))
                    if ref and conf > best_conf:
                        best_conf, best_ref, best_margin, best_pos = conf, ref, margin, (nx, ny)
            if best_ref is None or best_conf < CONFIDENCE_FLOOR or best_margin < CONFIDENCE_MARGIN:
                continue
            detections.append(
                Detection(
                    hero_id=best_ref["id"],
                    localized_name=best_ref["localized_name"],
                    confidence=round(best_conf, 4),
                    margin=round(best_margin, 4),
                    x=int(best_pos[0]),
                    y=int(best_pos[1]),
                    size=tile,
                )
            )
        return detections

    @staticmethod
    def _dedupe(dets: list[Detection], max_heroes: int, image_size: tuple[int, int]) -> dict:
        dets.sort(key=lambda d: -d.confidence)
        kept: list[Detection] = []
        for d in dets:
            clash = False
            for k in kept:
                if abs(d.x - k.x) < 0.5 * k.size and abs(d.y - k.y) < 0.5 * k.size:
                    clash = True
                    break
            if not clash:
                kept.append(d)
            if len(kept) >= max_heroes * 3:
                break

        # Prefer one detection per hero, keeping the highest confidence.
        by_hero: dict[int, Detection] = {}
        for d in kept:
            if d.hero_id not in by_hero or d.confidence > by_hero[d.hero_id].confidence:
                by_hero[d.hero_id] = d
        final = sorted(by_hero.values(), key=lambda d: (d.y, d.x))[:max_heroes]
        return {
            "detected": [d.to_dict() for d in final],
            "hero_ids": [d.hero_id for d in final],
            "count": len(final),
            "image_size": {"width": image_size[0], "height": image_size[1]},
            "confidence_floor": CONFIDENCE_FLOOR,
            "confidence_margin": CONFIDENCE_MARGIN,
        }
