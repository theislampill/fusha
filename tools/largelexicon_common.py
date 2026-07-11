"""Shared helpers for the largelexicon implementation lane.

The largelexicon lane is source-addressed and source-clean. It expands from the
repo-owned Qamus dataset, emits reviewable samples in git, and writes full
generated outputs only when the caller asks for them. It does not touch live
Qamus and does not import external corpus text.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import uuid
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import normalize_ar as N  # noqa: E402
QAMUS_ENTRIES = ROOT / "qamus" / "data" / "current" / "entries.jsonl"
QAMUS_ENTRIES_MIN = ROOT / "qamus" / "data" / "current" / "entries.min.jsonl"
LEXICON_DIR = ROOT / "fusha" / "lexicon" / "largelexicon"
MORPH_EXAMPLE_DIR = ROOT / "fusha" / "morphology" / "examples"
MORPH_DATA_DIR = ROOT / "fusha" / "morphology" / "data"
PARSER_EVAL_DIR = ROOT / "fusha" / "parser" / "eval"
PARSER_MODEL_CARD_DIR = ROOT / "fusha" / "parser" / "model-cards"
REPORT_DIR = ROOT / "qamus" / "reports"
QAMUS_LARGELX_DIR = ROOT / "qamus" / "indexes" / "largelexicon"
HOMOGRAPH_KEYS = QAMUS_LARGELX_DIR / "homograph-keys.json"
HYGIENE_REPORT = QAMUS_LARGELX_DIR / "hygiene-report.json"
ALLOWLIST = LEXICON_DIR / "source-clean-table-allowlist.json"
LEMMA_SAMPLE = LEXICON_DIR / "lemma-source.sample.jsonl"
FORM_SAMPLE = LEXICON_DIR / "form-source.sample.jsonl"
LEMMA_FULL = LEXICON_DIR / "lemma-source.full.jsonl"
FORM_FULL = LEXICON_DIR / "form-source.full.jsonl"
STEM_SAMPLE = MORPH_EXAMPLE_DIR / "largelexicon-stems.sample.jsonl"
STEM_FULL = MORPH_DATA_DIR / "largelexicon-stems.full.jsonl"
QWORD_DENOMINATOR_FULL = QAMUS_LARGELX_DIR / "qamus-qword-denominator.full.jsonl"
QWORD_DENOMINATOR_MANIFEST = QAMUS_LARGELX_DIR / "qamus-qword-denominator.manifest.json"
QWORD_DENOMINATOR_ENTRY_INDEX = QAMUS_LARGELX_DIR / "qamus-qword-denominator.entry-shard-index.json"
QWORD_DENOMINATOR_SOURCE_REPAIR = QAMUS_LARGELX_DIR / "qamus-qword-denominator.source-card-repair.json"
QWORD_DENOMINATOR_SHARD_DIR = QAMUS_LARGELX_DIR / "qword-denominator"
QWORD_CROSSWALK_MANIFEST = QAMUS_LARGELX_DIR / "qamus-qword-crosswalk.manifest.json"
QWORD_CROSSWALK_SHARD_DIR = QAMUS_LARGELX_DIR / "qword-crosswalk"
SOURCE_CARD_REPAIR_DIR = ROOT / "qamus" / "repairs" / "source-card-examples"
SOURCE_CARD_REPAIR_WORKLIST = SOURCE_CARD_REPAIR_DIR / "source-card-repair-worklist.jsonl"
SOURCE_CARD_REPAIR_META = SOURCE_CARD_REPAIR_DIR / "source-card-repair-worklist.meta.json"
FULL_TABLE_META = QAMUS_LARGELX_DIR / "source-clean-fact-tables.meta.json"

PUBLIC_BOUNDARY = {"src": "qamus", "kind": "authored", "lang": "en"}
SOURCE_STATUS = "qamus_current_authored"
SCHEMA_PREFIX = "fusha/largelexicon"

FORBIDDEN_PUBLIC_SUBSTRINGS = {
    "mcp",
    "tafsir",
    "qac",
    "quran.com",
    "quranic arabic corpus",
    "/srv/",
    "c:\\",
    "source photo",
    "source-photo",
    "ocr",
}

GENERATION_MANIFEST_NAME = "GENERATION.json"
GENERATION_STALE_LOCK_SECONDS = 6 * 60 * 60

# Build-time root certification is intentionally narrower than Arabic-text
# normalization.  Tatweel is presentation-only, and final-radical alif maqsurah
# is represented as ya for root identity.  Display/scripture text is untouched.
ROOT_SHAPE_PATTERN = re.compile(r"^[ء-ي]( [ء-ي]){1,4}$")
SURFACE_ALTERNATE_PATTERN = re.compile(r"\s*(?:/|؛|;|،|,|\||>|\s[-–—]\s)\s*")
QURAN_SINGLE_REF_PATTERN = re.compile(r"^(\d{1,3}):(\d{1,3})$")
QURAN_RANGE_REF_PATTERN = re.compile(r"^(\d{1,3}):(\d{1,3})[-–—](\d{1,3})$")


class WriterLockError(RuntimeError):
    """Raised when a shard-family writer cannot acquire exclusive ownership."""


@lru_cache(maxsize=None)
def _forbidden_label_pattern(label: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(label)}\b", re.IGNORECASE)


def match_forbidden_labels(text_lower: str, labels: Iterable[str]) -> list[str]:
    """Boundary-aware forbidden-label matching.

    Labels containing '/', '\\', '.', or a space retain substring semantics.
    Other labels match only as regex word-bounded tokens. The caller supplies
    lowercased text; regex matching remains case-insensitive for safety.
    """
    matches: list[str] = []
    for label in labels:
        label_lower = str(label).lower()
        if not label_lower:
            continue
        if any(marker in label_lower for marker in ("/", "\\", ".", " ")):
            matched = label_lower in text_lower
        else:
            matched = bool(_forbidden_label_pattern(label_lower).search(text_lower))
        if matched:
            matches.append(label)
    return matches

KNOWN_QWORD_SOURCE_CARD_REPAIR_HINTS = {
    "n993": {
        "source_photo_page_image": "pg443.jpeg",
        "candidate_quran_ref": "42:47",
        "note": "Owner-supplied source card shows Qur'anic usage absent from qamus/data/current/entries.jsonl.",
    }
}


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_value(*args: str) -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(ROOT), *args], text=True, encoding="utf-8", stderr=subprocess.DEVNULL
        )
        return out.strip()
    except Exception:
        return "unknown"


def freshness(status: str = "active", stale_after: str = "qamus_data_or_source_schema_change") -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "generated_by": "tools.largelexicon_common",
        "source_head": git_value("rev-parse", "HEAD"),
        "source_branch": git_value("rev-parse", "--abbrev-ref", "HEAD"),
        "supersedes": [],
        "stale_after": stale_after,
        "status": status,
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def repo_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_jsonl_rows(rows: Iterable[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(row, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def writer_lock_path(target_dir: Path) -> Path:
    return target_dir.with_name(f"{target_dir.name}.lock")


def previous_generation_path(target_dir: Path) -> Path:
    return target_dir.with_name(f"{target_dir.name}.prev")


def _staging_generation_path(target_dir: Path) -> Path:
    return target_dir.with_name(f"{target_dir.name}.staging-{os.getpid()}")


def writer_lock_status(
    target_dir: Path, *, stale_after_seconds: int = GENERATION_STALE_LOCK_SECONDS
) -> dict[str, Any]:
    """Inspect a lock without stealing it.

    Six hours is the conservative default stale threshold.  Age is advisory:
    even an older lock is never removed automatically; an operator must first
    confirm that its recorded PID/writer is no longer active and remove it.
    """
    path = writer_lock_path(target_dir)
    if not path.exists():
        return {"exists": False, "path": str(path), "stale": False}
    try:
        details = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        details = {"unreadable": True}
    age_seconds = max(0.0, datetime.now(UTC).timestamp() - path.stat().st_mtime)
    return {
        "exists": True,
        "path": str(path),
        "stale": age_seconds >= stale_after_seconds,
        "age_seconds": age_seconds,
        "stale_after_seconds": stale_after_seconds,
        "details": details,
    }


@contextmanager
def exclusive_writer_lock(
    target_dir: Path,
    *,
    writer_id: str,
    stale_after_seconds: int = GENERATION_STALE_LOCK_SECONDS,
) -> Iterator[dict[str, Any]]:
    """Hold the fail-closed O_EXCL lock beside ``target_dir``.

    Stale locks are reported but never auto-stolen, including locks younger
    than the documented threshold.  Manual removal requires out-of-band proof
    that the recorded writer is dead.
    """
    target_dir = Path(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    path = writer_lock_path(target_dir)
    token = uuid.uuid4().hex
    acquired_at = now_iso()
    payload = {
        "schema": "fusha/largelexicon-writer-lock@1",
        "pid": os.getpid(),
        "writer_id": writer_id,
        "acquired_at": acquired_at,
        "stale_after_seconds": stale_after_seconds,
        "token": token,
    }
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as exc:
        status = writer_lock_status(target_dir, stale_after_seconds=stale_after_seconds)
        stale_text = "stale-candidate" if status.get("stale") else "active-or-young"
        raise WriterLockError(
            f"writer lock exists at {path} ({stale_text}); second writer fails closed. "
            "Never auto-steal it; verify the recorded process is dead before manual removal."
        ) from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        yield payload
    finally:
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
            if current.get("token") == token:
                path.unlink()
        except (FileNotFoundError, OSError, ValueError):
            pass


def _fsync_file(path: Path) -> None:
    with path.open("r+b") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    """Best-effort directory durability (supported on Linux; harmless on Windows)."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def write_json_atomic(path: Path, obj: dict[str, Any]) -> None:
    """Write a JSON file completely, then atomically replace its file path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
    try:
        write_json(temporary, obj)
        _fsync_file(temporary)
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def _safe_shard_name(name: str) -> str:
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix != ".jsonl":
        raise ValueError(f"unsafe shard path: {name!r}")
    return relative.as_posix()


def _jsonl_row_count(path: Path) -> tuple[int, list[str]]:
    count = 0
    errors: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            count += 1
            try:
                json.loads(line)
            except ValueError as exc:
                errors.append(f"{path.name}:{line_no}: invalid JSON: {exc}")
    return count, errors


def verify_generation(target_dir: Path, *, allow_legacy: bool = True) -> dict[str, Any]:
    """Cheaply detect missing, extra, truncated, or mixed-generation shards.

    A pre-RM-19 directory with no ``GENERATION.json`` remains valid when
    ``allow_legacy`` is true.  Once the sidecar exists, every JSONL shard must
    match its declared row count and SHA-256 exactly.
    """
    target_dir = Path(target_dir)
    generation_path = target_dir / GENERATION_MANIFEST_NAME
    if not target_dir.is_dir():
        return {"ok": False, "legacy": False, "errors": [f"missing generation directory: {target_dir}"]}
    if not generation_path.exists():
        if allow_legacy:
            return {"ok": True, "legacy": True, "errors": [], "path": str(target_dir)}
        return {"ok": False, "legacy": False, "errors": [f"missing {GENERATION_MANIFEST_NAME}"]}
    try:
        generation = json.loads(generation_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"ok": False, "legacy": False, "errors": [f"invalid {GENERATION_MANIFEST_NAME}: {exc}"]}

    errors: list[str] = []
    declared_rows = generation.get("shards")
    if not isinstance(declared_rows, list):
        return {"ok": False, "legacy": False, "errors": ["GENERATION.json shards must be a list"]}
    declared: dict[str, dict[str, Any]] = {}
    for shard in declared_rows:
        if not isinstance(shard, dict) or not isinstance(shard.get("path"), str):
            errors.append("GENERATION.json contains an invalid shard record")
            continue
        try:
            name = _safe_shard_name(shard["path"])
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if name in declared:
            errors.append(f"duplicate declared shard: {name}")
        declared[name] = shard

    actual = {
        path.relative_to(target_dir).as_posix()
        for path in target_dir.rglob("*.jsonl")
        if path.is_file()
    }
    expected = set(declared)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            errors.append(f"missing shards: {missing}")
        if extra:
            errors.append(f"unexpected shards: {extra}")
    actual_total = 0
    for name in sorted(expected & actual):
        path = target_dir / name
        row_count, row_errors = _jsonl_row_count(path)
        actual_total += row_count
        errors.extend(row_errors)
        shard = declared[name]
        if row_count != shard.get("row_count"):
            errors.append(f"{name}: row_count mismatch: {row_count} != {shard.get('row_count')}")
        digest = sha256_file(path)
        if digest != shard.get("sha256"):
            errors.append(f"{name}: sha256 mismatch: {digest} != {shard.get('sha256')}")
    if generation.get("shard_count") != len(declared):
        errors.append(f"shard_count mismatch: {generation.get('shard_count')} != {len(declared)}")
    if generation.get("row_count") != actual_total:
        errors.append(f"generation row_count mismatch: {generation.get('row_count')} != {actual_total}")
    return {
        "ok": not errors,
        "legacy": False,
        "errors": errors,
        "path": str(target_dir),
        "generation": generation,
    }


def generation_fingerprint(target_dir: Path) -> str:
    """Hash all generation file names and bytes to reject stale writer inputs."""
    target_dir = Path(target_dir)
    if not target_dir.exists():
        return "missing"
    digest = hashlib.sha256()
    for path in sorted(item for item in target_dir.rglob("*") if item.is_file()):
        digest.update(path.relative_to(target_dir).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _remove_staging_dirs(target_dir: Path) -> None:
    for path in target_dir.parent.glob(f"{target_dir.name}.staging-*"):
        if path.is_dir():
            shutil.rmtree(path)


def _recover_generation_unlocked(target_dir: Path) -> dict[str, Any]:
    """Recover the tiny gap between ``current -> .prev`` and staging promotion.

    Deterministic policy: a present current directory wins.  If current is
    absent and ``.prev`` exists, restore ``.prev`` and discard staging debris.
    This chooses the last known-good generation rather than guessing whether a
    staged generation was intended to become live.
    """
    previous = previous_generation_path(target_dir)
    if target_dir.exists():
        _remove_staging_dirs(target_dir)
        return {"action": "current_present", "path": str(target_dir)}
    if previous.exists():
        os.rename(previous, target_dir)
        _remove_staging_dirs(target_dir)
        _fsync_directory(target_dir.parent)
        return {"action": "restored_previous", "path": str(target_dir)}
    staging = sorted(target_dir.parent.glob(f"{target_dir.name}.staging-*"))
    valid = [path for path in staging if path.is_dir() and verify_generation(path, allow_legacy=False)["ok"]]
    if len(valid) == 1:
        os.rename(valid[0], target_dir)
        _remove_staging_dirs(target_dir)
        _fsync_directory(target_dir.parent)
        return {"action": "promoted_only_complete_staging", "path": str(target_dir)}
    if staging:
        raise RuntimeError(
            f"cannot recover {target_dir}: no prior generation and {len(valid)} of {len(staging)} staging dirs validate"
        )
    return {"action": "nothing_to_recover", "path": str(target_dir)}


def recover_generation(target_dir: Path, *, writer_id: str = "largelexicon-recovery") -> dict[str, Any]:
    with exclusive_writer_lock(target_dir, writer_id=writer_id):
        return _recover_generation_unlocked(Path(target_dir))


def atomic_promote_shards(
    target_dir: Path,
    shards: Mapping[str, Iterable[dict[str, Any]]],
    *,
    writer_id: str,
    promoted_at: str | None = None,
    after_row: Callable[[Path, dict[str, Any]], None] | None = None,
    after_current_to_previous: Callable[[], None] | None = None,
    after_promote: Callable[[dict[str, Any]], None] | None = None,
    expected_current_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Validate and promote one complete shard generation under a writer lock.

    Directory replacement is intentionally two renames because portable
    Windows/Linux APIs cannot atomically exchange non-empty directories.  The
    tiny interval with no current directory is recovered deterministically by
    :func:`recover_generation`, which restores ``.prev``.
    """
    target_dir = Path(target_dir)
    names = [_safe_shard_name(name) for name in shards]
    if len(set(names)) != len(names):
        raise ValueError("duplicate shard paths")
    normalized = {name: shards[original] for name, original in zip(names, shards)}
    staging = _staging_generation_path(target_dir)
    previous = previous_generation_path(target_dir)
    with exclusive_writer_lock(target_dir, writer_id=writer_id):
        _recover_generation_unlocked(target_dir)
        if target_dir.exists():
            current_check = verify_generation(target_dir)
            if not current_check["ok"]:
                raise RuntimeError(f"refusing to replace invalid current generation: {current_check['errors']}")
        if expected_current_fingerprint is not None:
            actual_fingerprint = generation_fingerprint(target_dir)
            if actual_fingerprint != expected_current_fingerprint:
                raise RuntimeError(
                    "current generation changed after writer input was read; refusing stale promotion"
                )
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        moved_current = False
        promoted_new = False
        try:
            generation_shards: list[dict[str, Any]] = []
            total_rows = 0
            for name in sorted(normalized):
                path = staging / name
                path.parent.mkdir(parents=True, exist_ok=True)
                row_count = 0
                with path.open("w", encoding="utf-8", newline="\n") as handle:
                    for row in normalized[name]:
                        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                        handle.write("\n")
                        row_count += 1
                        if after_row is not None:
                            after_row(path, row)
                    handle.flush()
                    os.fsync(handle.fileno())
                total_rows += row_count
                generation_shards.append(
                    {"path": name, "row_count": row_count, "sha256": sha256_file(path)}
                )
            generation = {
                "schema": "fusha/largelexicon-shard-generation@1",
                "writer_id": writer_id,
                "promoted_at": promoted_at or now_iso(),
                "shard_count": len(generation_shards),
                "row_count": total_rows,
                "shards": generation_shards,
            }
            write_json(staging / GENERATION_MANIFEST_NAME, generation)
            _fsync_file(staging / GENERATION_MANIFEST_NAME)
            staged_check = verify_generation(staging, allow_legacy=False)
            if not staged_check["ok"]:
                raise RuntimeError(f"staged generation failed validation: {staged_check['errors']}")
            _fsync_directory(staging)

            if previous.exists():
                shutil.rmtree(previous)
            if target_dir.exists():
                os.rename(target_dir, previous)
                moved_current = True
                _fsync_directory(target_dir.parent)
            if after_current_to_previous is not None:
                after_current_to_previous()
            os.rename(staging, target_dir)
            promoted_new = True
            _fsync_directory(target_dir.parent)
            live_check = verify_generation(target_dir, allow_legacy=False)
            if not live_check["ok"]:
                raise RuntimeError(f"promoted generation failed validation: {live_check['errors']}")
            if after_promote is not None:
                after_promote(generation)
            return generation
        except Exception:
            if promoted_new and target_dir.exists():
                shutil.rmtree(target_dir)
            if not target_dir.exists() and moved_current and previous.exists():
                os.rename(previous, target_dir)
                _fsync_directory(target_dir.parent)
            if staging.exists():
                shutil.rmtree(staging)
            raise


def rollback_generation(
    target_dir: Path,
    *,
    writer_id: str = "largelexicon-rollback",
    after_rollback: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Swap ``target_dir`` with its single preserved ``.prev`` generation."""
    target_dir = Path(target_dir)
    previous = previous_generation_path(target_dir)
    temporary = target_dir.with_name(f"{target_dir.name}.rollback-{os.getpid()}")
    with exclusive_writer_lock(target_dir, writer_id=writer_id):
        _recover_generation_unlocked(target_dir)
        if not target_dir.exists() or not previous.exists():
            raise RuntimeError(f"rollback requires both {target_dir} and {previous}")
        if temporary.exists():
            shutil.rmtree(temporary)
        os.rename(target_dir, temporary)
        try:
            os.rename(previous, target_dir)
            os.rename(temporary, previous)
            _fsync_directory(target_dir.parent)
        except Exception:
            if target_dir.exists() and temporary.exists() and not previous.exists():
                os.rename(target_dir, previous)
                os.rename(temporary, target_dir)
            elif not target_dir.exists() and temporary.exists():
                os.rename(temporary, target_dir)
            raise
        result = verify_generation(target_dir)
        if not result["ok"]:
            raise RuntimeError(f"rolled-back generation failed validation: {result['errors']}")
        if after_rollback is not None:
            after_rollback()
        return {"action": "rolled_back", "verification": result}


def unique_keep_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        value = (value or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def normalize_build_root(root: str) -> str:
    """Normalize a root fact at build time without altering source text.

    The root-only policy strips tatweel (including ``هـ`` notation), collapses
    whitespace, and represents a final radical ``ى`` as ``ي``.  The final-
    radical mapping is applied only to an otherwise letter-shaped 2--5 radical
    candidate, never to a surface word copied into the root field.
    """
    normalized = " ".join((root or "").replace("ـ", "").split())
    radicals = normalized.split()
    if 2 <= len(radicals) <= 5 and all(re.fullmatch(r"[ء-ي]", item) for item in radicals):
        if radicals[-1] == "ى":
            radicals[-1] = "ي"
        normalized = " ".join(radicals)
    return normalized


def is_root_shape(root: str) -> bool:
    """Return whether *root* is exactly 2--5 space-separated Arabic radicals."""
    return bool(ROOT_SHAPE_PATTERN.fullmatch(root or ""))


def root_hygiene(raw_root: str) -> dict[str, Any]:
    """Represent valid single/dual roots and fail closed on malformed input."""
    source = (raw_root or "").strip()
    if not source:
        return {
            "root": None,
            "roots": [],
            "root_source": None,
            "no_root_reason": None,
            "risk_flags": [],
        }
    parts = [normalize_build_root(part) for part in re.split(r"\s*/\s*", source)]
    if not parts or any(not is_root_shape(part) for part in parts):
        return {
            "root": None,
            "roots": [],
            "root_source": source,
            "no_root_reason": "malformed_root",
            "risk_flags": ["malformed_root"],
        }
    roots = unique_keep_order(parts)
    return {
        "root": roots[0] if len(roots) == 1 else None,
        "roots": roots,
        "root_source": source,
        "no_root_reason": None,
        "risk_flags": [],
    }


def normalize_build_surface(surface: str) -> str:
    """Strip presentation-only tatweel from a generated lookup surface."""
    return (surface or "").replace("ـ", "").strip()


def is_single_arabic_token(surface: str) -> bool:
    """Accept one Arabic letter/mark token and reject spaces or punctuation."""
    normalized = normalize_build_surface(surface)
    if not normalized:
        return False
    has_letter = False
    for character in normalized:
        category = unicodedata.category(character)
        if not (category.startswith("L") or category.startswith("M")):
            return False
        if "ARABIC" not in unicodedata.name(character, ""):
            return False
        has_letter = has_letter or category.startswith("L")
    return has_letter


def split_surface_alternates(surface: str) -> list[str]:
    """Split explicit alternate delimiters; phrases remain invalid phrases."""
    return unique_keep_order(SURFACE_ALTERNATE_PATTERN.split(surface or ""))


def surface_hygiene(raw_surface: str) -> dict[str, Any]:
    """Route an authored surface to accepted tokens or an explicit repair queue."""
    source = (raw_surface or "").strip()
    if re.search(r"[A-Za-z]", source):
        return {
            "source": source,
            "surfaces": [],
            "rejected": [source] if source else [],
            "route": "entry_repair_queue",
            "risk_flags": ["gloss_bearing_surface"],
        }
    candidates = split_surface_alternates(source)
    accepted = [normalize_build_surface(item) for item in candidates if is_single_arabic_token(item)]
    rejected = [item for item in candidates if not is_single_arabic_token(item)]
    flags: list[str] = []
    if rejected or (source and not accepted):
        flags.append("malformed_surface")
    return {
        "source": source,
        "surfaces": unique_keep_order(accepted),
        "rejected": rejected,
        "route": "entry_repair_queue" if flags else ("alternate_split" if len(accepted) > 1 else "accepted"),
        "risk_flags": flags,
    }


def quran_ref_hygiene(reference: str | None) -> dict[str, Any]:
    """Represent single and range ayah references without guessing word identity."""
    value = (reference or "").strip()
    range_match = QURAN_RANGE_REF_PATTERN.fullmatch(value)
    if range_match:
        surah, start, end = (int(item) for item in range_match.groups())
        return {
            "ref": value,
            "ref_kind": "range",
            "surah": surah,
            "ayah_start": start,
            "ayah_end": end,
            "risk_flags": ["range_reference"],
        }
    single_match = QURAN_SINGLE_REF_PATTERN.fullmatch(value)
    if single_match:
        surah, ayah = (int(item) for item in single_match.groups())
        return {
            "ref": value,
            "ref_kind": "single",
            "surah": surah,
            "ayah": ayah,
            "risk_flags": [],
        }
    return {
        "ref": value or None,
        "ref_kind": "malformed",
        "risk_flags": ["malformed_reference"],
    }


def split_headword(headword: str) -> list[str]:
    parts = re.split(r"\s*/\s*|\s+؛\s+|\s+,\s+", headword or "")
    return unique_keep_order(parts)


def raw_forms_for_entry(entry: dict[str, Any]) -> list[str]:
    """Return source-authored form cells before the single-token hygiene gate."""
    forms: list[str] = []
    forms.extend(split_headword(entry.get("headword", "")))
    for sense in entry.get("senses") or []:
        forms.extend(split_headword(sense.get("ar", "")))
    for usage in entry.get("usage") or []:
        forms.extend(usage.get("forms") or [])
    return unique_keep_order(forms)


def forms_for_entry(entry: dict[str, Any]) -> list[str]:
    """Return only build-safe, single-token Arabic surfaces.

    Rejected source cells remain visible through the hygiene report; this
    function never repairs the read-only Qamus entry dataset.
    """
    forms: list[str] = []
    for source in raw_forms_for_entry(entry):
        forms.extend(surface_hygiene(source)["surfaces"])
    return unique_keep_order(forms)


def build_homograph_key_inventory(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build deterministic broad-normalization collisions across distinct roots."""
    by_key: dict[str, dict[str, dict[str, set[str]]]] = defaultdict(
        lambda: defaultdict(lambda: {"entry_ids": set(), "surfaces": set()})
    )
    for entry in entries:
        root_result = root_hygiene(entry.get("root") or "")
        if not root_result["roots"]:
            continue
        for surface in forms_for_entry(entry):
            norm_key = N.norm(surface)
            if not norm_key:
                continue
            for root in root_result["roots"]:
                by_key[norm_key][root]["entry_ids"].add(entry["id"])
                by_key[norm_key][root]["surfaces"].add(surface)
    inventory: list[dict[str, Any]] = []
    for norm_key in sorted(by_key):
        root_map = by_key[norm_key]
        if len(root_map) < 2:
            continue
        inventory.append(
            {
                "norm_key": norm_key,
                "root_count": len(root_map),
                "roots": sorted(root_map),
                "entries": [
                    {
                        "root": root,
                        "entry_ids": sorted(root_map[root]["entry_ids"]),
                        "surfaces": sorted(root_map[root]["surfaces"]),
                    }
                    for root in sorted(root_map)
                ],
            }
        )
    return inventory


@lru_cache(maxsize=1)
def committed_homograph_norm_keys() -> frozenset[str]:
    if not HOMOGRAPH_KEYS.exists():
        return frozenset()
    payload = json.loads(HOMOGRAPH_KEYS.read_text(encoding="utf-8"))
    return frozenset(item["norm_key"] for item in payload.get("keys") or [])


def section_to_pos(section: str, tags: Iterable[str] = ()) -> str:
    text = " ".join([section or "", *(tags or [])]).lower()
    if "particle" in text:
        return "particle"
    if "verb" in text:
        return "verb"
    if "proper" in text or "name" in text:
        return "proper_noun"
    if "noun" in text:
        return "noun"
    return "unknown"


def no_root_reason(entry: dict[str, Any], pos: str) -> str | None:
    root_result = root_hygiene(entry.get("root") or "")
    if root_result["no_root_reason"]:
        return root_result["no_root_reason"]
    if root_result["roots"]:
        return None
    if pos == "particle":
        return "function_only_no_root"
    if pos == "proper_noun":
        return "proper_name_no_root"
    return "qamus_entry_no_root_recorded"


def gloss_hint(entry: dict[str, Any]) -> str:
    for sense in entry.get("senses") or []:
        gloss = (sense.get("gloss") or "").strip()
        if gloss:
            return gloss
    return (entry.get("meaning") or entry.get("definition") or entry.get("gloss") or "").strip()


def qg_class_for_pos(pos: str) -> str:
    return {
        "particle": "qg-particle",
        "verb": "qg-verb-stem",
        "proper_noun": "qg-proper-noun",
        "noun": "qg-noun-stem",
    }.get(pos, "qg-noun-stem")


def entry_to_lemma(entry: dict[str, Any]) -> dict[str, Any]:
    pos = section_to_pos(entry.get("section", ""), entry.get("tags") or [])
    forms = forms_for_entry(entry)
    root_result = root_hygiene(entry.get("root") or "")
    return {
        "schema": f"{SCHEMA_PREFIX}/lemma-source@1",
        "entry_id": entry["id"],
        "source_keys": entry.get("source_keys") or [],
        "lemma": entry.get("headword"),
        "root": root_result["root"],
        "roots": root_result["roots"],
        "root_source": root_result["root_source"],
        "no_root_reason": no_root_reason(entry, pos),
        "pos": pos,
        "forms": forms,
        "gloss_hint": gloss_hint(entry),
        "source_status": SOURCE_STATUS,
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "risk_flags": risk_flags(entry, pos, forms),
    }


def form_rows_for_lemmas(lemmas: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lemma in lemmas:
        for index, form in enumerate(lemma.get("forms") or []):
            rows.append(
                {
                    "schema": f"{SCHEMA_PREFIX}/form-source@1",
                    "form_id": f"llx_form_{lemma['entry_id']}_{index:03d}",
                    "entry_id": lemma["entry_id"],
                    "source_keys": lemma["source_keys"],
                    "surface": form,
                    "surface_norm_strict": N.norm_strict(form),
                    "surface_bare": N.bare(form),
                    "lemma": lemma["lemma"],
                    "root": lemma["root"],
                    "roots": lemma["roots"],
                    "no_root_reason": lemma["no_root_reason"],
                    "pos": lemma["pos"],
                    "source_status": lemma["source_status"],
                    "public_boundary": lemma["public_boundary"],
                    "risk_flags": lemma.get("risk_flags") or [],
                }
            )
    return rows


def risk_flags(entry: dict[str, Any], pos: str, forms: list[str]) -> list[str]:
    flags: list[str] = []
    root_result = root_hygiene(entry.get("root") or "")
    if not entry.get("root"):
        flags.append("no_root_recorded")
    flags.extend(root_result["risk_flags"])
    if pos == "particle":
        flags.append("requires_nahw_function")
    if pos == "unknown":
        flags.append("unknown_pos")
    if len(forms) == 0:
        flags.append("no_listed_forms")
    if any("/" in (entry.get("headword") or "") for _ in [0]):
        flags.append("compound_headword")
    if any(N.norm(form) in committed_homograph_norm_keys() for form in forms):
        flags.append("norm_homograph")
    return unique_keep_order(flags)


def stem_rows_for_entry(entry: dict[str, Any]) -> list[dict[str, Any]]:
    lemma = entry_to_lemma(entry)
    rows: list[dict[str, Any]] = []
    for index, form in enumerate(lemma["forms"]):
        surface = form.strip()
        if not surface:
            continue
        rows.append(
            {
                "schema": f"{SCHEMA_PREFIX}/stem-source@1",
                "stem_id": f"llx_{entry['id']}_{index:03d}",
                "generation_key": f"qamus:{entry['id']}:{index:03d}",
                "entry_id": entry["id"],
                "source_keys": entry.get("source_keys") or [],
                "surface": surface,
                "surface_norm_strict": N.norm_strict(surface),
                "surface_bare": N.bare(surface),
                "lemma": lemma["lemma"],
                "root": lemma["root"],
                "roots": lemma["roots"],
                "no_root_reason": lemma["no_root_reason"],
                "pos": lemma["pos"],
                "pattern": None,
                "form": None,
                "gloss_shape": gloss_shape(lemma["pos"]),
                "gloss_hint": lemma["gloss_hint"],
                "visible_segments": [
                    {
                        "surface": surface,
                        "role": role_for_pos(lemma["pos"]),
                        "qg_class": qg_class_for_pos(lemma["pos"]),
                        "gloss": lemma["gloss_hint"] or surface,
                    }
                ],
                "features": {},
                "qamus_entry_refs": entry.get("source_keys") or [],
                "source": "qamus_current_authored",
                "source_status": "qamus_current_authored",
                "risk_flags": lemma["risk_flags"],
                "public_boundary": dict(PUBLIC_BOUNDARY),
            }
        )
    return rows


def qword_denominator_rows(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compact all-visible-qword denominator rows for Qamus-owned example cards.

    The row preserves bidirectional handles without repeating full translation
    prose or importing any external source payload. It is a denominator and
    routing table, not a deployable hover table.
    """
    rows: list[dict[str, Any]] = []
    for entry in entries:
        for usage_index, usage in enumerate(entry.get("usage") or [], start=1):
            for example_index, example in enumerate(usage.get("examples") or [], start=1):
                card_id = f"{entry['id']}:u{usage_index}:e{example_index}"
                card_text = example.get("ar") or ""
                ref_result = quran_ref_hygiene(example.get("ref"))
                words = [word for word in card_text.split() if word]
                for qword_index, surface in enumerate(words, start=1):
                    rows.append(
                        {
                            "schema": "qamus/largelexicon-qword-denominator@1",
                            "row_id": f"llx-qword-{entry['id']}-{usage_index:02d}-{example_index:02d}-{qword_index:03d}",
                            "entry_id": entry["id"],
                            "source_keys": entry.get("source_keys") or [],
                            "card_id": card_id,
                            "usage_index": usage_index,
                            "example_index": example_index,
                            "qword_index": qword_index,
                            "visible_surface": surface,
                            "visible_surface_norm_strict": N.norm_strict(surface),
                            "card_text_sha256": sha256_text(card_text),
                            "quran_ref": example.get("ref"),
                            "ref_kind": ref_result["ref_kind"],
                            "ref_range": (
                                {
                                    "surah": ref_result["surah"],
                                    "ayah_start": ref_result["ayah_start"],
                                    "ayah_end": ref_result["ayah_end"],
                                }
                                if ref_result["ref_kind"] == "range"
                                else None
                            ),
                            "canonical_quran_loc": None,
                            "canonical_wbw_loc": None,
                            "route": (
                                "range_reference_review"
                                if ref_result["ref_kind"] == "range"
                                else "qamus_executor_source_crosswalk"
                            ),
                            "status": (
                                "denominator_range_reference_excluded_from_identity_acceptance"
                                if ref_result["ref_kind"] == "range"
                                else "denominator_needs_source_address_crosswalk"
                            ),
                            "risk_flags": ref_result["risk_flags"],
                            "source_status": SOURCE_STATUS,
                            "public_boundary": dict(PUBLIC_BOUNDARY),
                            "live_mutation_allowed": False,
                        }
                    )
    return rows


def _source_key_parts(source_key: str) -> tuple[str, int]:
    match = re.match(r"^([pvn])(\d+)$", source_key or "")
    if not match:
        return ("z", 0)
    return (match.group(1), int(match.group(2)))


def _source_key_sort_key(source_key: str) -> tuple[int, int, str]:
    prefix, number = _source_key_parts(source_key)
    prefix_order = {"p": 0, "v": 1, "n": 2}.get(prefix, 9)
    return (prefix_order, number, source_key or "")


def _format_source_key(prefix: str, number: int) -> str:
    width = 3 if number < 1000 else 4
    return f"{prefix}{number:0{width}d}"


def _primary_source_key(row: dict[str, Any]) -> str:
    keys = row.get("source_keys") or []
    if not keys:
        return "z000"
    return sorted(keys, key=_source_key_sort_key)[0]


def qword_shard_label(row: dict[str, Any], shard_size: int = 40) -> tuple[str, dict[str, Any]]:
    source_key = _primary_source_key(row)
    prefix, number = _source_key_parts(source_key)
    if prefix == "z" or number <= 0:
        return "misc", {"prefix": "misc", "start": None, "end": None}
    start = ((number - 1) // shard_size) * shard_size + 1
    end = start + shard_size - 1
    if prefix == "p":
        end = min(end, 100)
    elif prefix == "v":
        end = min(end, 947)
    elif prefix == "n":
        end = min(end, 1045)
    label = f"{_format_source_key(prefix, start)}-{_format_source_key(prefix, end)}"
    return label, {"prefix": prefix, "start": start, "end": end}


def _qword_row_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _source_key_sort_key(_primary_source_key(row)),
        row.get("entry_id") or "",
        row.get("usage_index") or 0,
        row.get("example_index") or 0,
        row.get("qword_index") or 0,
        row.get("row_id") or "",
    )


def write_qword_denominator_shards(
    rows: Iterable[dict[str, Any]],
    *,
    shard_size: int = 40,
    all_entries: Iterable[dict[str, Any]] | None = None,
    _after_row: Callable[[Path, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Write qword denominator shards plus manifest and entry reverse index.

    This preserves Project-Xanadu-style bidirectionality: the logical table is
    still one addressable denominator, but each entry can jump directly to its
    shard and every shard is hash/count guarded.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ranges: dict[str, dict[str, Any]] = {}
    for row in sorted(rows, key=_qword_row_sort_key):
        label, range_info = qword_shard_label(row, shard_size=shard_size)
        grouped[label].append(row)
        ranges[label] = range_info
    all_entry_lookup = {entry["id"]: entry for entry in (all_entries or [])}
    all_entry_id_set = set(all_entry_lookup)

    shards: list[dict[str, Any]] = []
    shard_payloads: dict[str, list[dict[str, Any]]] = {}
    entry_index: dict[str, dict[str, Any]] = {}
    total_rows = 0
    for label in sorted(grouped, key=lambda value: _source_key_sort_key(value.split("-")[0] if "-" in value else value)):
        shard_rows = grouped[label]
        shard_name = f"{label}.jsonl"
        shard_path = QWORD_DENOMINATOR_SHARD_DIR / shard_name
        shard_payloads[shard_name] = shard_rows
        total_rows += len(shard_rows)
        entry_ids = sorted({row["entry_id"] for row in shard_rows})
        source_keys = sorted({_primary_source_key(row) for row in shard_rows}, key=_source_key_sort_key)
        for entry_id in entry_ids:
            rows_for_entry = [row for row in shard_rows if row["entry_id"] == entry_id]
            entry_index[entry_id] = {
                "path": repo_rel(shard_path),
                "row_count": len(rows_for_entry),
                "source_keys": rows_for_entry[0].get("source_keys") or [],
                "first_row_id": rows_for_entry[0].get("row_id"),
                "last_row_id": rows_for_entry[-1].get("row_id"),
            }
        shards.append(
            {
                "path": repo_rel(shard_path),
                "schema": "qamus/largelexicon-qword-denominator@1",
                "row_count": len(shard_rows),
                "sha256": sha256_jsonl_rows(shard_rows),
                "first_row_id": shard_rows[0].get("row_id"),
                "last_row_id": shard_rows[-1].get("row_id"),
                "source_key_range": ranges[label],
                "first_source_key": source_keys[0] if source_keys else None,
                "last_source_key": source_keys[-1] if source_keys else None,
                "entry_count": len(entry_ids),
            }
        )

    common_freshness = freshness(status="active", stale_after="qamus_entries_or_largelexicon_schema_change")
    entries_with_rows = set(entry_index)
    entries_without_rows = sorted(all_entry_id_set - entries_with_rows)
    source_card_repairs = []
    for entry_id in entries_without_rows:
        entry = all_entry_lookup.get(entry_id) or {}
        source_card_repairs.append(
            {
                "schema": "qamus/largelexicon-qword-source-card-repair@1",
                "entry_id": entry_id,
                "source_keys": entry.get("source_keys") or [],
                "headword": entry.get("headword"),
                "section": entry.get("section"),
                "forms": forms_for_entry(entry) if entry else [],
                "total_uses": entry.get("total_uses"),
                "repair_hint": next(
                    (
                        KNOWN_QWORD_SOURCE_CARD_REPAIR_HINTS[source_key]
                        for source_key in (entry.get("source_keys") or [])
                        if source_key in KNOWN_QWORD_SOURCE_CARD_REPAIR_HINTS
                    ),
                    None,
                ),
                "reason": "qamus_current_entry_has_no_usage_example_rows_for_qword_denominator",
                "source_status": SOURCE_STATUS,
                "public_boundary": dict(PUBLIC_BOUNDARY),
                "live_mutation_allowed": False,
                "next_action": "repair source-card/example edge from source photo or canonical source, then regenerate qword denominator shards",
            }
        )
    source_card_repair_obj = {
        "schema": "qamus/largelexicon-qword-source-card-repair-list@1",
        **common_freshness,
        "table_id": "qamus-qword-denominator",
        "row_count": len(source_card_repairs),
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "repairs": source_card_repairs,
    }
    manifest = {
        "schema": "qamus/largelexicon-qword-denominator-manifest@1",
        **common_freshness,
        "table_id": "qamus-qword-denominator",
        "table_schema": "qamus/largelexicon-qword-denominator@1",
        "storage": "sharded_jsonl_manifest",
        "primary_key": "row_id",
        "row_count": total_rows,
        "shard_count": len(shards),
        "qamus_entry_count": len(all_entry_id_set) if all_entry_id_set else len(entries_with_rows),
        "entries_with_qword_rows": len(entries_with_rows),
        "entries_without_qword_rows": entries_without_rows,
        "shard_strategy": f"qamus_source_key_prefix_ordinal_ranges_{shard_size}",
        "entry_index_path": repo_rel(QWORD_DENOMINATOR_ENTRY_INDEX),
        "source_card_repair_path": repo_rel(QWORD_DENOMINATOR_SOURCE_REPAIR),
        "legacy_monolith_replaced": repo_rel(QWORD_DENOMINATOR_FULL),
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "claim_boundary": "Source-clean Qamus qword denominator only; not live Qamus progress.",
        "bidirectional_contract": {
            "forward_keys": [
                "entry_id",
                "source_keys",
                "card_id",
                "usage_index",
                "example_index",
                "qword_index",
                "visible_surface",
                "quran_ref",
            ],
            "reverse_keys": [
                "row_id",
                "entry_id",
                "card_id",
                "card_text_sha256",
            ],
            "crosswalk_keys": [
                "canonical_quran_loc",
                "canonical_wbw_loc",
                "route",
                "status",
            ],
        },
        "shards": shards,
    }
    entry_index_obj = {
        "schema": "qamus/largelexicon-qword-entry-shard-index@1",
        **common_freshness,
        "table_id": "qamus-qword-denominator",
        "manifest_path": repo_rel(QWORD_DENOMINATOR_MANIFEST),
        "entry_count": len(entry_index),
        "qamus_entry_count": len(all_entry_id_set) if all_entry_id_set else len(entries_with_rows),
        "entries_with_qword_rows": len(entries_with_rows),
        "entries_without_qword_rows": entries_without_rows,
        "row_count": total_rows,
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "entries": dict(sorted(entry_index.items())),
    }
    def install_sidecars(_generation: dict[str, Any]) -> None:
        # The external table manifest is installed last: readers either see
        # the old manifest or the complete new one, never a partial JSON file.
        write_json_atomic(QWORD_DENOMINATOR_SOURCE_REPAIR, source_card_repair_obj)
        write_json_atomic(QWORD_DENOMINATOR_ENTRY_INDEX, entry_index_obj)
        write_json_atomic(QWORD_DENOMINATOR_MANIFEST, manifest)

    atomic_promote_shards(
        QWORD_DENOMINATOR_SHARD_DIR,
        shard_payloads,
        writer_id="tools.largelexicon_common.write_qword_denominator_shards",
        after_row=_after_row,
        after_promote=install_sidecars,
    )
    if QWORD_DENOMINATOR_FULL.exists():
        QWORD_DENOMINATOR_FULL.unlink()
    return manifest


def full_table_allowlist() -> dict[str, Any]:
    return {
        "schema": f"{SCHEMA_PREFIX}/source-clean-table-allowlist@1",
        **freshness(status="active", stale_after="qamus_entries_or_largelexicon_schema_change"),
        "claim_boundary": (
            "Only source-clean Qamus-authored generated fact tables are committed. "
            "Raw QAC/MCP/Quran.com/Tafsir payloads remain private evidence/cache data."
        ),
        "runtime_dependency_policy": "dependency_free; no external package or live API required at parse time",
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "tables": [
            {
                "path": repo_rel(LEMMA_FULL),
                "schema": f"{SCHEMA_PREFIX}/lemma-source@1",
                "commit_allowed": True,
                "raw_external_allowed": False,
                "minimum_rows": 2092,
                "source": "qamus_current_authored",
            },
            {
                "path": repo_rel(FORM_FULL),
                "schema": f"{SCHEMA_PREFIX}/form-source@1",
                "commit_allowed": True,
                "raw_external_allowed": False,
                "minimum_rows": 7000,
                "source": "qamus_current_authored",
            },
            {
                "path": repo_rel(STEM_FULL),
                "schema": f"{SCHEMA_PREFIX}/stem-source@1",
                "commit_allowed": True,
                "raw_external_allowed": False,
                "minimum_rows": 7000,
                "source": "qamus_current_authored",
            },
            {
                "path": repo_rel(QWORD_DENOMINATOR_MANIFEST),
                "schema": "qamus/largelexicon-qword-denominator-manifest@1",
                "commit_allowed": True,
                "raw_external_allowed": False,
                "minimum_rows": 100000,
                "source": "qamus_current_authored",
                "storage": "sharded_jsonl_manifest",
                "entry_index_path": repo_rel(QWORD_DENOMINATOR_ENTRY_INDEX),
            },
            {
                "path": repo_rel(QWORD_CROSSWALK_MANIFEST),
                "schema": "qamus/largelexicon-qword-crosswalk-manifest@1",
                "commit_allowed": True,
                "raw_external_allowed": False,
                "minimum_rows": 100000,
                "source": "qamus_current_authored",
                "storage": "sharded_jsonl_manifest",
                "denominator_manifest_path": repo_rel(QWORD_DENOMINATOR_MANIFEST),
            },
        ],
        "private_only_sources": [
            "qac_raw_tsv",
            "mcp_raw_response",
            "quran_foundation_raw_response",
            "quran_com_raw_response",
            "source_photo_or_ocr_dump",
        ],
    }


def role_for_pos(pos: str) -> str:
    return {
        "particle": "function_token",
        "verb": "verb_stem",
        "proper_noun": "proper_name_host",
        "noun": "noun_host",
    }.get(pos, "surface_host")


def gloss_shape(pos: str) -> str:
    return {
        "particle": "function_token_requires_nahw",
        "verb": "form_sensitive_verb",
        "proper_noun": "proper_name",
        "noun": "nominal",
    }.get(pos, "surface_candidate")


def iter_entries(path: Path = QAMUS_ENTRIES) -> list[dict[str, Any]]:
    return read_jsonl(path)


def inventory(entries: list[dict[str, Any]]) -> dict[str, Any]:
    pos_counts = Counter(section_to_pos(e.get("section", ""), e.get("tags") or []) for e in entries)
    form_counts = [len(forms_for_entry(e)) for e in entries]
    empty_root = sum(1 for e in entries if not (e.get("root") or "").strip())
    return {
        "schema": f"{SCHEMA_PREFIX}/source-inventory@1",
        **freshness(),
        "source_files": {
            "entries": str(QAMUS_ENTRIES.relative_to(ROOT)),
            "entries_min": str(QAMUS_ENTRIES_MIN.relative_to(ROOT)),
        },
        "counts": {
            "entries": len(entries),
            "empty_root_entries": empty_root,
            "rooted_entries": len(entries) - empty_root,
            "listed_forms": sum(form_counts),
            "max_forms_per_entry": max(form_counts) if form_counts else 0,
        },
        "pos_counts": dict(sorted(pos_counts.items())),
        "public_boundary": dict(PUBLIC_BOUNDARY),
        "claim_boundary": "Qamus-authored source inventory only; not a general Arabic parser, not live Qamus progress.",
    }


def public_boundary_errors(row: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    boundary = row.get("public_boundary") or {}
    for key, value in PUBLIC_BOUNDARY.items():
        if boundary.get(key) != value:
            errors.append(f"{label}: public_boundary.{key} must be {value!r}")
    text = json.dumps(row, ensure_ascii=False).lower()
    for forbidden in match_forbidden_labels(text, FORBIDDEN_PUBLIC_SUBSTRINGS):
        errors.append(f"{label}: forbidden public/source leak substring {forbidden!r}")
    return errors
