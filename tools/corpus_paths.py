"""Resolve the local ingest corpus directory WITHOUT baking a private path into
the public Fusha repo.

The raw APKG/PDF/DOCX corpus is a local, uncommitted input. Set the env var
``SARFNAHW_CORPUS_DIR`` to point the ingest tools at it, e.g.::

    SARFNAHW_CORPUS_DIR=/path/to/sarfnahw python tools/build_source_catalogue.py

Fallbacks (all git-ignored): ``./_in/sarfnahw`` then ``./corpora/sarfnahw/_in``.
Committed artifacts use file *basenames* only — never absolute paths.
"""
import os


def corpus_dir():
    env = os.environ.get("SARFNAHW_CORPUS_DIR")
    if env:
        return env
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in ("_in/sarfnahw", "corpora/sarfnahw/_in"):
        cand = os.path.join(here, rel)
        if os.path.isdir(cand):
            return cand
    return os.path.join(here, "_in", "sarfnahw")


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
