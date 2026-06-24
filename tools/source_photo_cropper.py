#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preprocess + crop a source page image into a readable entry-block tile (PIL/cv2). READ-ONLY on the corpus.

Calibrated on the owner sample pages (columnar layout: red headword band, green "Quranic Usage" band, numbered
entry blocks). Steps: orient/deskew -> CLAHE contrast -> optional upscale -> save a tile for visual verification
(the visual read is the AUTHORITY; OCR is only a candidate generator). No image bytes are committed to the repo.

Usage: python tools/source_photo_cropper.py <image> --out tile.png [--rotate 90] [--upscale 1.5]
"""
import argparse
import os
import sys

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None


def preprocess(path, out, rotate=0, upscale=1.0, clahe=True):
    if cv2 is None:
        print("cv2/numpy not available", file=sys.stderr); return False
    img = cv2.imread(path)
    if img is None:
        print("could not read", path, file=sys.stderr); return False
    if rotate:
        k = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}.get(rotate)
        if k is not None:
            img = cv2.rotate(img, k)
    if upscale and upscale != 1.0:
        img = cv2.resize(img, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)
    if clahe:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
        img = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    cv2.imwrite(out, img)
    return True


def detect_orientation(path):
    """Heuristic: portrait pages of this dictionary are wider-than-tall when photographed sideways."""
    if cv2 is None:
        return 0
    img = cv2.imread(path)
    if img is None:
        return 0
    h, w = img.shape[:2]
    return 90 if w > h * 1.2 else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rotate", type=int, default=None)
    ap.add_argument("--upscale", type=float, default=1.3)
    a = ap.parse_args()
    rot = a.rotate if a.rotate is not None else detect_orientation(a.image)
    ok = preprocess(a.image, a.out, rotate=rot, upscale=a.upscale)
    print("ok" if ok else "fail", "->", a.out, "(rotate=%s)" % rot)


if __name__ == "__main__":
    main()
