#!/usr/bin/env python3
"""Build the ONTO qg reconciliation and palette collision artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from qg_registry import (
    DEFAULT_CSS_PATH,
    MATRIX_PATH,
    REGISTRY_PATH,
    ROOT,
    build_collision_matrix,
    build_registry,
    dump_json,
    read_schema,
    render_collision_markdown,
    render_reconciliation_markdown,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--css", type=Path, default=DEFAULT_CSS_PATH, help="live wbw.css input")
    parser.add_argument("--write", action="store_true", help="write the requested registry artifacts")
    args = parser.parse_args(argv)
    css_path = args.css.resolve()
    css_text = css_path.read_text(encoding="utf-8")
    registry = build_registry(css_text, read_schema(), css_source="../../data/wbw.css")
    matrix = build_collision_matrix(registry)
    if args.write:
        dump_json(REGISTRY_PATH, registry)
        REGISTRY_PATH.with_suffix(".md").write_text(render_reconciliation_markdown(registry), encoding="utf-8", newline="\n")
        dump_json(MATRIX_PATH, matrix)
        MATRIX_PATH.with_suffix(".md").write_text(render_collision_markdown(matrix), encoding="utf-8", newline="\n")
        print(f"wrote {REGISTRY_PATH.relative_to(ROOT)}")
        print(f"wrote {REGISTRY_PATH.with_suffix('.md').relative_to(ROOT)}")
        print(f"wrote {MATRIX_PATH.relative_to(ROOT)}")
        print(f"wrote {MATRIX_PATH.with_suffix('.md').relative_to(ROOT)}")
    else:
        print(f"live_css_class_count={registry['inventory']['live_css_class_count']}")
        print(f"schema_enum_count={registry['inventory']['schema_enum_count']}")
        print(f"valid_final_count={registry['inventory']['valid_final_count']}")
        print(f"static_contrast_failures={registry['accessibility_floor']['failure_count']}")
        for theme in ("dark", "light"):
            print(f"{theme}_flagged_pairs={matrix['themes'][theme]['summary']['flagged_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
