#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repository evidence resolution for website-payload ``evidence_refs`` (stdlib only).

Standalone resolver: it is not yet wired into ``tools/validate_website_payload.py``
and never touches payload files. Given one evidence reference string (as it
appears in ``projection.evidence_refs``), it resolves the reference against the
committed typed-fact certification authority in this repository and reports a
closed, fail-closed effective state -- never a copied status string.

Four kinds of committed repository authority are consulted:

* the typed-fact certification event trails, folded through
  ``tools.certify_typed_fact.TypedFactCertificationStore`` (the fold and trail
  validation are reused, never reimplemented here);
* the candidate proof-particle contract
  (``qamus/examples/proof-particle/particle-contract.json``), whose facts are
  documented candidate evidence and are never certification authority no
  matter what their own posture fields claim;
* the configured two-vote artifact bundles, validated through
  ``tools.validate_two_vote_artifacts.validate``/``iter_jsonl`` (never
  reimplemented here) -- a valid ``two_vote_verified`` artifact is review
  evidence on its own (``review_verified``) and only becomes certification
  authority (``certified_support``) when a certification event trail
  explicitly binds it to a typed fact that is *currently* effectively
  certified;
* ``cert-event:<seq>:<fact_id>`` references, resolved against the exact
  committed event of that id in the same certification stores, reported
  against that fact_id's *current* effective state (a historical certifying
  event whose fact was later superseded/revoked is not authority);
* ``dawahwiki:<opaque_ref>#sha256:<hex>`` private-custody references,
  verified only against the bounded, structurally-filtered custody manifests
  committed under ``qamus/task-packets`` (docs/evidence-custody.md section
  2). This is provenance/custody verification only -- it never manufactures
  a typed fact and is never certification authority.

Everything else (MCP evidence, example corpora, lattice or candidate-payload
refs, and any scheme this module does not recognise) is out of scope for this
round and resolves as ``unsupported_scheme`` -- present but never
authoritative.

No filesystem writes, no certification-store mutation, and no import-time
side effects: everything below only reads committed files when a resolver
instance is constructed or asked to resolve a reference.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.certify_typed_fact import CertificationError, TypedFactCertificationStore  # noqa: E402
from tools import validate_two_vote_artifacts  # noqa: E402

# The exactly two committed typed-fact certification event stores in this
# worktree, relative to a resolver's repo_root. Membership here is a
# deliberate edit, not a filesystem scan: an uncommitted or unlisted directory
# is never folded in as authority.
CERTIFICATION_STORE_RELATIVE_DIRS: Tuple[str, ...] = (
    "qamus/examples/p007-li-pilot/certification",
    "qamus/certification/p007-geometry-wave",
)

# Candidate-only proof-particle contract. Every fact it declares carries a
# candidate evidence posture (e.g. ``source_addressed_candidate``); none of
# them is governed by a certification event trail, so none can ever resolve
# as certified authority.
PROOFP_CONTRACT_RELATIVE = "qamus/examples/proof-particle/particle-contract.json"

# The exactly two committed two-vote artifact bundles this resolver consults,
# relative to a resolver's repo_root. Membership here is a deliberate edit,
# not a filesystem scan: an uncommitted or unlisted bundle is never folded in
# as evidence, and a broken bundle voids the whole set (no partial trust).
TWO_VOTE_ARTIFACT_BUNDLE_RELATIVE_PATHS: Tuple[str, ...] = (
    "qamus/examples/p007-li-pilot/two-vote-artifacts.v1_1.jsonl",
    "qamus/examples/two_vote_artifact_v11_canaries.jsonl",
)

# Bounded directory for committed private-custody manifests (docs/evidence-
# custody.md section 2). Only direct ``*.json`` children of this directory
# are ever read -- never a recursive scan -- and only those whose parsed
# JSON structurally carries ``custody.out_of_git_evidence`` are treated as
# custody manifests; every other committed task packet in this directory is
# excluded by that structural filter, never ingested as authority.
CUSTODY_MANIFEST_DIRECTORY_RELATIVE = "qamus/task-packets"

_CUSTODY_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

# The closed effective-state vocabulary this round distinguishes. A resolver
# result outside this set is a bug, not a valid outcome.
EFFECTIVE_STATES: FrozenSet[str] = frozenset({
    "certified",
    "candidate",
    "review_required",
    "revoked",
    "invalidated",
    "dependency_failed",
    "evidence_unresolved",
    "unsupported_scheme",
    "contradictory",
    "certified_support",
    "review_verified",
    "custody_verified",
    "custody_hash_mismatch",
    "custody_invalid",
})

# Typed-fact certification-store status -> closed effective-state vocabulary.
# ``blocked`` means an active defeater currently invalidates a fact (doc
# section 5.3); ``rejected`` means review_required evidence was permanently
# refused certification. Neither is trusted as authority, so the exact label
# only matters for diagnostics. A status this module has never seen is
# refused rather than guessed at.
_STATUS_TO_EFFECTIVE: Dict[str, str] = {
    "candidate": "candidate",
    "pending": "candidate",
    "review_required": "review_required",
    "certified": "certified",
    "blocked": "invalidated",
    "rejected": "revoked",
}


@dataclass(frozen=True)
class EvidenceResolution:
    """The resolved outcome for exactly one evidence reference. Never mutated."""

    reference: str
    scheme: str
    present: bool
    effective_state: str
    authoritative_for_certification: bool
    reason: str
    source_locator: Optional[str]


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def effective_typed_fact_state(
    fact_id: str,
    folded_state: Dict[str, dict],
    *,
    _visiting: FrozenSet[str] = frozenset(),
) -> Tuple[str, bool, str]:
    """Pure recursive helper: effective state of one folded typed fact.

    ``folded_state`` is the shape ``TypedFactCertificationStore.state()``
    returns: ``fact_id -> {"status": ..., "fact": {...}}``. Only a currently
    certified fact whose every ``dependencies.fact_ids`` entry is itself
    effectively certified is authoritative; a missing dependency, a
    dependency cycle, or any non-certified status fails closed.
    """

    if fact_id in _visiting:
        return (
            "dependency_failed",
            False,
            "dependency cycle detected: %s is already being resolved" % fact_id,
        )
    entry = folded_state.get(fact_id)
    if entry is None:
        return (
            "evidence_unresolved",
            False,
            "fact_id %s is not registered in the folded certification state" % fact_id,
        )
    status = entry.get("status")
    effective_state = _STATUS_TO_EFFECTIVE.get(status)
    if effective_state is None:
        return (
            "evidence_unresolved",
            False,
            "fact_id %s carries an unrecognised certification status %r" % (fact_id, status),
        )
    if effective_state != "certified":
        return (
            effective_state,
            False,
            "fact_id %s is %s, not certified authority" % (fact_id, effective_state),
        )
    dependency_ids = ((entry.get("fact") or {}).get("dependencies") or {}).get("fact_ids") or []
    visiting = _visiting | {fact_id}
    for dependency_id in dependency_ids:
        dep_state, dep_authoritative, dep_reason = effective_typed_fact_state(
            dependency_id, folded_state, _visiting=visiting
        )
        if not dep_authoritative:
            return (
                "dependency_failed",
                False,
                "certified fact %s depends on %s, which is %s: %s"
                % (fact_id, dependency_id, dep_state, dep_reason),
            )
    return (
        "certified",
        True,
        "fact_id %s is certified with every required dependency effectively certified" % fact_id,
    )


class _StoreView:
    """Folded, conflict-checked state across every committed certification store.

    Loaded once per resolver instance; never re-read from disk after
    construction, so repeated ``resolve()`` calls against the same instance
    see a consistent snapshot.

    Typed-fact authority is all-or-nothing across the *configured* stores: a
    missing, unreadable/malformed, or trail-validation-failing store makes
    ``authority_intact`` False for this whole snapshot, and no fact_id folded
    from any (even individually valid) store is trusted. A store whose trail
    cannot be trusted could hide a conflicting or superseding event for a
    fact_id another store also carries, so partial trust is not safe.
    """

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.state: Dict[str, dict] = {}
        self.origin: Dict[str, str] = {}
        self.store_errors: Dict[str, List[str]] = {}
        self.integrity_errors: List[str] = []
        # Raw certification events keyed by their own event_id, and the set of
        # fact_ids each two-vote artifact_id was ever used to certify -- both
        # only populated once every configured store is trail-valid, folded,
        # and conflict-free (see below): a cert-event: or two-vote-artifact:
        # reference is no more trustworthy than the fact: scheme it rides on.
        self.events_by_id: Dict[str, dict] = {}
        self.two_vote_bound_fact_ids: Dict[str, Set[str]] = {}
        conflicting: set = set()
        intact_stores: List[Tuple[str, TypedFactCertificationStore]] = []
        for relative_dir in CERTIFICATION_STORE_RELATIVE_DIRS:
            directory = self.repo_root / relative_dir
            if not (directory / "events.jsonl").exists():
                # Never mkdir a store that is not already committed: that
                # would be a filesystem write for a repo_root this store does
                # not actually govern. A configured-but-uncommitted store is
                # an authority-integrity gap, not silent absence.
                self.integrity_errors.append(
                    "configured certification store %s has no committed events.jsonl"
                    % relative_dir
                )
                continue
            store = TypedFactCertificationStore(directory)
            try:
                errors = store.validate_trail()
            except CertificationError as exc:
                self.integrity_errors.append(
                    "certification store %s event trail is unreadable: %s" % (relative_dir, exc)
                )
                continue
            if errors:
                self.store_errors[relative_dir] = errors
                self.integrity_errors.append(
                    "certification store %s failed trail validation (%d error(s))"
                    % (relative_dir, len(errors))
                )
                continue
            intact_stores.append((relative_dir, store))

        self.authority_intact: bool = not self.integrity_errors
        if self.authority_intact:
            for relative_dir, store in intact_stores:
                try:
                    folded_state = store.state()
                except CertificationError as exc:
                    # A trail that validated cleanly should never fail to fold;
                    # this is a defensive fail-closed net, not an expected path.
                    self.integrity_errors.append(
                        "certification store %s could not be folded: %s" % (relative_dir, exc)
                    )
                    self.authority_intact = False
                    break
                for fact_id, entry in folded_state.items():
                    if fact_id in self.state:
                        if _canonical(self.state[fact_id]) != _canonical(entry):
                            conflicting.add(fact_id)
                        continue
                    self.state[fact_id] = entry
                    self.origin[fact_id] = relative_dir
                for event in store._events():
                    event_id = event.get("event_id")
                    if isinstance(event_id, str) and event_id:
                        self.events_by_id[event_id] = event
                    evidence_bundle_ref = event.get("evidence_bundle_ref")
                    if event.get("to_status") == "certified" and isinstance(evidence_bundle_ref, dict):
                        artifact_id = evidence_bundle_ref.get("two_vote_artifact_id")
                        fact_id = event.get("fact_id")
                        if artifact_id and fact_id:
                            self.two_vote_bound_fact_ids.setdefault(artifact_id, set()).add(fact_id)

        if not self.authority_intact:
            # No partial trust: an integrity failure anywhere in the configured
            # store set voids every fact_id this snapshot would otherwise fold.
            self.state = {}
            self.origin = {}
            conflicting = set()
            self.events_by_id = {}
            self.two_vote_bound_fact_ids = {}
        self.conflicts: FrozenSet[str] = frozenset(conflicting)


class _TwoVoteView:
    """Folded, conflict-checked index across the configured two-vote bundles.

    Every configured bundle is validated with
    ``tools.validate_two_vote_artifacts.validate`` (never reimplemented here)
    and, only if it passes, indexed by ``artifact_id`` via that module's own
    ``iter_jsonl``. Trust is all-or-nothing across the *configured* bundle
    set, exactly like ``_StoreView``: a missing, unreadable, validator-failing,
    or duplicate-conflicting bundle voids every artifact_id this snapshot
    would otherwise index.
    """

    def __init__(self, repo_root: Path):
        self.rows: Dict[str, dict] = {}
        self.origin: Dict[str, str] = {}
        self.integrity_errors: List[str] = []
        conflicting: set = set()
        for relative_path in TWO_VOTE_ARTIFACT_BUNDLE_RELATIVE_PATHS:
            full_path = repo_root / relative_path
            if not full_path.exists():
                self.integrity_errors.append(
                    "configured two-vote artifact bundle %s has no committed file" % relative_path
                )
                continue
            try:
                count, errors = validate_two_vote_artifacts.validate(str(full_path))
            except (OSError, ValueError) as exc:
                self.integrity_errors.append(
                    "configured two-vote artifact bundle %s is unreadable: %s" % (relative_path, exc)
                )
                continue
            if errors:
                self.integrity_errors.append(
                    "configured two-vote artifact bundle %s failed validation (%d error(s))"
                    % (relative_path, len(errors))
                )
                continue
            if count == 0:
                self.integrity_errors.append(
                    "configured two-vote artifact bundle %s carries zero rows" % relative_path
                )
                continue
            try:
                rows = list(validate_two_vote_artifacts.iter_jsonl(str(full_path)))
            except OSError as exc:
                self.integrity_errors.append(
                    "configured two-vote artifact bundle %s is unreadable: %s" % (relative_path, exc)
                )
                continue
            for _line_no, row in rows:
                if not isinstance(row, dict) or "__json_error__" in row:
                    self.integrity_errors.append(
                        "configured two-vote artifact bundle %s could not be safely indexed" % relative_path
                    )
                    continue
                artifact_id = row.get("artifact_id")
                if not artifact_id:
                    self.integrity_errors.append(
                        "configured two-vote artifact bundle %s carries a row with no artifact_id" % relative_path
                    )
                    continue
                if artifact_id in self.rows:
                    if _canonical(self.rows[artifact_id]) != _canonical(row):
                        conflicting.add(artifact_id)
                    continue
                self.rows[artifact_id] = row
                self.origin[artifact_id] = relative_path

        if conflicting:
            self.integrity_errors.append(
                "duplicate conflicting two-vote artifact_id(s) across configured bundles: %s"
                % ", ".join(sorted(conflicting))
            )

        self.authority_intact: bool = not self.integrity_errors
        if not self.authority_intact:
            # No partial trust: a broken bundle voids every artifact_id this
            # snapshot would otherwise index, including from the other,
            # individually-valid, configured bundle.
            self.rows = {}
            self.origin = {}


class _CustodyView:
    """Bounded, structurally-filtered custody-manifest index.

    Only direct ``*.json`` children of ``CUSTODY_MANIFEST_DIRECTORY_RELATIVE``
    are read (never a recursive scan), and only those whose parsed JSON
    structurally carries a non-empty ``custody.out_of_git_evidence`` list are
    treated as custody manifests -- every other committed task packet in that
    directory is excluded by that structural filter alone, never ingested as
    authority. A manifest that fails to parse is skipped, never trusted and
    never a crash.
    """

    def __init__(self, repo_root: Path):
        self.index: Dict[str, List[Dict[str, object]]] = {}
        directory = repo_root / CUSTODY_MANIFEST_DIRECTORY_RELATIVE
        if not directory.is_dir():
            return
        for path in sorted(directory.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, UnicodeDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            custody = payload.get("custody")
            if not isinstance(custody, dict):
                continue
            out_of_git_evidence = custody.get("out_of_git_evidence")
            if not isinstance(out_of_git_evidence, list) or not out_of_git_evidence:
                continue
            produced_by_lane = payload.get("produced_by_lane")
            reconstruction = custody.get("reconstruction")
            manifest_valid = bool(
                isinstance(produced_by_lane, str) and produced_by_lane.strip()
            ) and bool(isinstance(reconstruction, str) and reconstruction.strip())
            source = "%s/%s" % (CUSTODY_MANIFEST_DIRECTORY_RELATIVE, path.name)
            for row in out_of_git_evidence:
                if not isinstance(row, dict):
                    continue
                opaque_ref = row.get("opaque_ref")
                file_sha256 = row.get("file_sha256")
                if not opaque_ref or not file_sha256:
                    continue
                self.index.setdefault(opaque_ref, []).append({
                    "source": source,
                    "file_sha256": file_sha256,
                    "produced_by_lane": produced_by_lane,
                    "reconstruction": reconstruction,
                    "manifest_valid": manifest_valid,
                })


class WebsiteEvidenceResolver:
    """Resolves ``evidence_refs`` strings against one explicit repository root."""

    def __init__(self, repo_root: "os.PathLike[str] | str" = ROOT):
        self.repo_root = Path(repo_root)
        self._view = _StoreView(self.repo_root)
        self._two_vote_view = _TwoVoteView(self.repo_root)
        self._custody_view = _CustodyView(self.repo_root)
        self._proofp_facts: Optional[Dict[str, dict]] = None

    def _repo_relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.repo_root.resolve()).as_posix()
        except (OSError, ValueError):
            return path.name

    def _load_proofp_facts(self) -> Dict[str, dict]:
        if self._proofp_facts is not None:
            return self._proofp_facts
        facts: Dict[str, dict] = {}
        path = self.repo_root / PROOFP_CONTRACT_RELATIVE
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                payload = {}
            for fact in payload.get("facts") or []:
                if isinstance(fact, dict) and fact.get("fact_id"):
                    facts[str(fact["fact_id"])] = fact
        self._proofp_facts = facts
        return facts

    def resolve(self, reference: str) -> EvidenceResolution:
        """Resolve one reference. Never raises for a merely unresolvable ref."""

        ref = str(reference)
        if ":" not in ref:
            return EvidenceResolution(
                ref, ref, False, "unsupported_scheme", False,
                "reference %r carries no scheme prefix" % ref, None,
            )
        scheme, _, rest = ref.partition(":")
        if scheme == "two-vote-artifact":
            return self._resolve_two_vote_artifact(ref)
        if scheme == "cert-event":
            return self._resolve_cert_event(ref, rest)
        if scheme == "dawahwiki":
            return self._resolve_dawahwiki_custody(ref)
        if scheme != "fact":
            return EvidenceResolution(
                ref, scheme, False, "unsupported_scheme", False,
                "scheme %r is not a supported evidence-reference scheme in this round" % scheme,
                None,
            )
        namespace, _, remainder = rest.partition(":")
        if not namespace or not remainder:
            return EvidenceResolution(
                ref, scheme, False, "evidence_unresolved", False,
                "malformed fact reference %r carries no namespace/identifier" % ref, None,
            )

        # 1. Direct fact_id lookup across every committed certification store
        #    whose event trail validated cleanly. A conflicting duplicate
        #    fact_id across stores is reported, never silently picked.
        if ref in self._view.conflicts:
            return EvidenceResolution(
                ref, scheme, True, "contradictory", False,
                "fact_id %r is registered with conflicting content in more than one "
                "committed certification store" % ref, None,
            )
        if ref in self._view.state:
            origin_dir = self._view.origin[ref]
            locator = self._repo_relative(self.repo_root / origin_dir / "events.jsonl")
            effective_state, authoritative, reason = effective_typed_fact_state(
                ref, self._view.state
            )
            return EvidenceResolution(
                ref, scheme, True, effective_state, authoritative, reason, locator,
            )

        # 2. Candidate proof-particle contract (namespace "proofp"). Its facts
        #    are documented candidate evidence, never certification authority,
        #    regardless of their own posture fields.
        if namespace == "proofp":
            proofp_fact = self._load_proofp_facts().get(remainder)
            if proofp_fact is not None:
                posture = (proofp_fact.get("evidence") or {}).get("status") or "unlabelled"
                return EvidenceResolution(
                    ref, scheme, True, "candidate", False,
                    "proof-particle contract evidence (%s) is candidate-only and is never "
                    "certification authority regardless of its own posture fields" % posture,
                    self._repo_relative(self.repo_root / PROOFP_CONTRACT_RELATIVE),
                )

        # 3. A typed-fact reference (anything other than the independent
        #    proofp candidate namespace) can never resolve while any
        #    configured certification store is missing, unreadable, or fails
        #    trail validation: an unverifiable authority trail could hide a
        #    conflicting or superseding event, so this fails closed rather
        #    than silently falling back to whatever the intact stores show.
        if namespace != "proofp" and not self._view.authority_intact:
            return EvidenceResolution(
                ref, scheme, False, "contradictory", False,
                "typed-fact certification authority is not intact for this "
                "resolver snapshot (%s); no fact: reference can resolve as "
                "authoritative until every configured certification store is "
                "committed and passes trail validation"
                % "; ".join(self._view.integrity_errors),
                None,
            )

        # 4. Nothing in committed repository authority resolves this reference.
        return EvidenceResolution(
            ref, scheme, False, "evidence_unresolved", False,
            "no committed certification-store fact_id or candidate contract entry "
            "matches %r" % ref, None,
        )

    def _bound_certified_fact_for_two_vote_artifact(self, artifact_id: str) -> Optional[str]:
        """The fact_id of a currently effectively-certified fact this artifact_id
        certified, if any -- never guessed from occurrence/surface, only from
        the certification event trail's own evidence-bundle binding."""

        if not self._view.authority_intact:
            return None
        for fact_id in sorted(self._view.two_vote_bound_fact_ids.get(artifact_id) or ()):
            _effective_state, authoritative, _reason = effective_typed_fact_state(
                fact_id, self._view.state
            )
            if authoritative:
                return fact_id
        return None

    def _resolve_two_vote_artifact(self, ref: str) -> EvidenceResolution:
        scheme = "two-vote-artifact"
        if not self._two_vote_view.authority_intact:
            return EvidenceResolution(
                ref, scheme, False, "contradictory", False,
                "two-vote-artifact evidence authority is not intact for this resolver "
                "snapshot (%s); no two-vote-artifact: reference can resolve until every "
                "configured two-vote artifact bundle is committed and passes validation"
                % "; ".join(self._two_vote_view.integrity_errors),
                None,
            )
        row = self._two_vote_view.rows.get(ref)
        if row is None:
            return EvidenceResolution(
                ref, scheme, False, "evidence_unresolved", False,
                "no committed two-vote artifact bundle row matches artifact_id %r" % ref, None,
            )
        locator = self._two_vote_view.origin.get(ref)
        bound_fact_id = self._bound_certified_fact_for_two_vote_artifact(ref)
        if bound_fact_id is not None:
            return EvidenceResolution(
                ref, scheme, True, "certified_support", True,
                "two-vote artifact %r (%s) is explicitly bound by a certification event "
                "trail to fact_id %r, which is currently effectively certified"
                % (ref, row.get("claim_state"), bound_fact_id),
                locator,
            )
        return EvidenceResolution(
            ref, scheme, True, "review_verified", False,
            "two-vote artifact %r (%s) is valid review evidence but is not bound by any "
            "certification event trail to a currently effectively certified typed fact"
            % (ref, row.get("claim_state")),
            locator,
        )

    def _resolve_cert_event(self, ref: str, rest: str) -> EvidenceResolution:
        scheme = "cert-event"
        event_seq, sep, fact_id = rest.partition(":")
        if not sep or not event_seq.isdigit() or not fact_id:
            return EvidenceResolution(
                ref, scheme, False, "evidence_unresolved", False,
                "malformed cert-event reference %r must be cert-event:<seq>:<fact_id>" % ref,
                None,
            )
        if not self._view.authority_intact:
            return EvidenceResolution(
                ref, scheme, False, "contradictory", False,
                "typed-fact certification authority is not intact for this resolver "
                "snapshot (%s); no cert-event: reference can resolve until every "
                "configured certification store is committed and passes trail validation"
                % "; ".join(self._view.integrity_errors),
                None,
            )
        # Exact event_id + fact_id agreement only: a numeric seq prefix alone
        # (without the exact fact_id it was recorded against) never matches.
        event = self._view.events_by_id.get(ref)
        if event is None or event.get("fact_id") != fact_id:
            return EvidenceResolution(
                ref, scheme, False, "evidence_unresolved", False,
                "no committed certification-store event_id matches %r" % ref, None,
            )
        effective_state, authoritative, reason = effective_typed_fact_state(
            fact_id, self._view.state
        )
        return EvidenceResolution(
            ref, scheme, True, effective_state, authoritative,
            "cert-event %r certified fact_id %r; current effective state: %s"
            % (ref, fact_id, reason),
            None,
        )

    def _resolve_dawahwiki_custody(self, ref: str) -> EvidenceResolution:
        scheme = "dawahwiki"
        opaque_ref, sep, hash_part = ref.partition("#sha256:")
        if not sep or not _CUSTODY_HASH_RE.match(hash_part):
            return EvidenceResolution(
                ref, scheme, False, "evidence_unresolved", False,
                "malformed dawahwiki custody reference %r must be "
                "<opaque_ref>#sha256:<64-lowercase-hex>" % ref,
                None,
            )
        entries = self._custody_view.index.get(opaque_ref)
        if not entries:
            return EvidenceResolution(
                ref, scheme, False, "evidence_unresolved", False,
                "no committed custody manifest under %s carries opaque_ref %r"
                % (CUSTODY_MANIFEST_DIRECTORY_RELATIVE, opaque_ref),
                None,
            )
        projections = {
            _canonical({
                "file_sha256": entry["file_sha256"],
                "produced_by_lane": entry["produced_by_lane"],
                "reconstruction": entry["reconstruction"],
            })
            for entry in entries
        }
        if len(projections) > 1:
            return EvidenceResolution(
                ref, scheme, True, "contradictory", False,
                "opaque_ref %r is registered with conflicting custody rows across "
                "committed manifests: %s"
                % (opaque_ref, ", ".join(sorted(str(entry["source"]) for entry in entries))),
                None,
            )
        entry = entries[0]
        if not entry["manifest_valid"]:
            return EvidenceResolution(
                ref, scheme, False, "custody_invalid", False,
                "custody manifest %s for opaque_ref %r is missing a non-empty "
                "produced_by_lane or custody.reconstruction" % (entry["source"], opaque_ref),
                None,
            )
        if entry["file_sha256"] != hash_part:
            return EvidenceResolution(
                ref, scheme, False, "custody_hash_mismatch", False,
                "custody manifest %s records file_sha256 %s for opaque_ref %r, which does "
                "not match the requested sha256:%s"
                % (entry["source"], entry["file_sha256"], opaque_ref, hash_part),
                None,
            )
        return EvidenceResolution(
            ref, scheme, True, "custody_verified", False,
            "custody manifest %s attests opaque_ref %r with matching file_sha256 and a "
            "non-empty producer + reconstruction" % (entry["source"], opaque_ref),
            str(entry["source"]),
        )

    def resolve_many(self, evidence_refs: Iterable[str]) -> List[EvidenceResolution]:
        """Resolve every reference; report all of them, dropping none."""

        return [self.resolve(reference) for reference in evidence_refs]


def resolve_evidence_refs(
    evidence_refs: Iterable[str],
    *,
    repo_root: "os.PathLike[str] | str" = ROOT,
) -> List[EvidenceResolution]:
    """Convenience entry point: resolve a batch of refs against repo_root."""

    return WebsiteEvidenceResolver(repo_root).resolve_many(evidence_refs)


def non_authoritative(resolutions: Iterable[EvidenceResolution]) -> List[EvidenceResolution]:
    """Every resolution that is not certification authority, contradictions included."""

    return [resolution for resolution in resolutions if not resolution.authoritative_for_certification]


def _event_sha256(event: dict) -> str:
    return "sha256:" + hashlib.sha256(_canonical(event).encode("utf-8")).hexdigest()


def _build_valid_authority_events(fact_id: str) -> List[dict]:
    """A minimal, hand-assembled, structurally valid certified event chain.

    Deliberately avoids ``fact_type``/``evidence_mode`` values that would pull
    in the two-vote-reopening or derived-cascade checks in
    ``TypedFactCertificationStore.validate_trail`` -- this is a self-test
    fixture for authority-integrity plumbing, not a certification-gate proof.
    """

    fact = {
        "fact_id": fact_id,
        "fact_type": "selftest_authority_integrity_fact",
        "evidence_mode": "selftest_direct",
        "dependencies": {"fact_ids": []},
    }
    register = {
        "schema": "qamus.certification_event.v1",
        "seq": 1,
        "prev_event_sha256": "genesis",
        "event_id": "cert-event:1:%s" % fact_id,
        "event_type": "register",
        "fact_id": fact_id,
        "contract_id": "selftest-contract",
        "fact_type": fact["fact_type"],
        "evidence_mode": fact["evidence_mode"],
        "from_status": None,
        "to_status": "candidate",
        "actor": "selftest",
        "timestamp": "2026-01-01T00:00:00Z",
        "reason": "selftest registration",
        "evidence_bundle_ref": None,
        "fact": fact,
    }
    to_review = {
        "schema": "qamus.certification_event.v1",
        "seq": 2,
        "prev_event_sha256": _event_sha256(register),
        "event_id": "cert-event:2:%s" % fact_id,
        "event_type": "transition",
        "fact_id": fact_id,
        "contract_id": "selftest-contract",
        "fact_type": fact["fact_type"],
        "evidence_mode": fact["evidence_mode"],
        "from_status": "candidate",
        "to_status": "review_required",
        "actor": "selftest",
        "timestamp": "2026-01-01T00:00:01Z",
        "reason": "selftest review",
        "evidence_bundle_ref": None,
        "triggered_by": None,
    }
    to_certified = {
        "schema": "qamus.certification_event.v1",
        "seq": 3,
        "prev_event_sha256": _event_sha256(to_review),
        "event_id": "cert-event:3:%s" % fact_id,
        "event_type": "transition",
        "fact_id": fact_id,
        "contract_id": "selftest-contract",
        "fact_type": fact["fact_type"],
        "evidence_mode": fact["evidence_mode"],
        "from_status": "review_required",
        "to_status": "certified",
        "actor": "selftest",
        "timestamp": "2026-01-01T00:00:02Z",
        "reason": "selftest certification",
        "evidence_bundle_ref": {"selftest": True},
        "triggered_by": None,
    }
    return [register, to_review, to_certified]


def _write_events_jsonl(directory: Path, lines: List[str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _focused_proof_authority_integrity() -> int:
    """Proof that a broken/missing configured store fails closed, never crashes.

    Every case below builds an isolated ``repo_root`` under a temporary
    directory created only here, at self-test execution time -- never at
    import time, and never touching this repository's own committed stores.
    """

    failures = 0
    good_relative_dir, bad_relative_dir = CERTIFICATION_STORE_RELATIVE_DIRS
    fact_id = "fact:selftest:authority-integrity:1"
    valid_events = [_canonical(event) for event in _build_valid_authority_events(fact_id)]

    def run_case(label: str, repo_root: Path) -> None:
        nonlocal failures
        try:
            resolver = WebsiteEvidenceResolver(repo_root)
            result = resolver.resolve(fact_id)
        except Exception as exc:  # noqa: BLE001 - a crash here is exactly the defect
            print("FAIL %s -> raised %s: %s" % (label, type(exc).__name__, exc))
            failures += 1
            return
        ok = not result.authoritative_for_certification
        print(
            ("ok   " if ok else "FAIL ")
            + "%s -> effective_state=%s authoritative=%s reason=%s"
            % (label, result.effective_state, result.authoritative_for_certification, result.reason)
        )
        if not ok:
            failures += 1

    with tempfile.TemporaryDirectory(prefix="website-evidence-resolver-selftest-") as tmp:
        tmp_root = Path(tmp)

        semantically_invalid_root = tmp_root / "semantically-invalid-second"
        _write_events_jsonl(semantically_invalid_root / good_relative_dir, valid_events)
        broken_register = dict(json.loads(valid_events[0]))
        broken_register["prev_event_sha256"] = "sha256:" + "0" * 64
        _write_events_jsonl(
            semantically_invalid_root / bad_relative_dir, [_canonical(broken_register)]
        )
        run_case(
            "7. valid store + semantically invalid parseable second store",
            semantically_invalid_root,
        )

        malformed_json_root = tmp_root / "malformed-json-second"
        _write_events_jsonl(malformed_json_root / good_relative_dir, valid_events)
        _write_events_jsonl(malformed_json_root / bad_relative_dir, ["{not valid json"])
        run_case("8. valid store + malformed JSON second store", malformed_json_root)

        missing_store_root = tmp_root / "missing-second-store"
        _write_events_jsonl(missing_store_root / good_relative_dir, valid_events)
        run_case("9. valid store + missing configured second store", missing_store_root)

    if failures:
        print("\n%d AUTHORITY-INTEGRITY PROOF CASE(S) FAILED" % failures)
        return 1
    print("\nALL AUTHORITY-INTEGRITY PROOF CASES PASSED")
    return 0


def _minimal_custody_manifest(*, opaque_ref: str, file_sha256: str, produced_by_lane: str = "selftest-lane") -> dict:
    """The minimal shape of a docs/evidence-custody.md §2 manifest row.

    Mirrors ``qamus/task-packets/tp-p007-ds-w1-covered-locs.json``: top-level
    ``produced_by_lane`` plus ``custody.out_of_git_evidence`` (opaque_ref +
    file_sha256) and ``custody.reconstruction``.
    """

    return {
        "schema": "qamus.coverage_manifest.v1",
        "manifest_id": "selftest-custody-manifest",
        "produced_by_lane": produced_by_lane,
        "custody": {
            "policy": "docs/evidence-custody.md section 2 (manifest + hash + reconstruction for out-of-git evidence)",
            "out_of_git_evidence": [
                {
                    "what": "selftest out-of-git evidence row",
                    "source_kind": "selftest",
                    "opaque_ref": opaque_ref,
                    "record_count": 1,
                    "file_sha256": file_sha256,
                }
            ],
            "reconstruction": "selftest fixture: illustrative only, not re-derivable",
        },
    }


def _write_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical(manifest), encoding="utf-8")


def _focused_proof_custody_manifest_integrity() -> int:
    """Isolated temporary-manifest proofs for custody-ref cases (i) and (j).

    Every repo_root below is built fresh under a temporary directory at
    self-test execution time; the committed
    ``qamus/task-packets/tp-p007-ds-w1-covered-locs.json`` fixture is never
    touched.
    """

    failures = 0
    opaque_ref = "dawahwiki:packets/selftest-custody/row.json"
    file_sha256 = "1" * 64
    custody_ref = "%s#sha256:%s" % (opaque_ref, file_sha256)
    manifest_relative = "qamus/task-packets/selftest-custody-manifest.json"

    def run_case(
        label: str,
        repo_root: Path,
        expected_present: bool,
        expected_state: str,
        expected_authoritative: bool,
    ) -> None:
        nonlocal failures
        resolver = WebsiteEvidenceResolver(repo_root)
        result = resolver.resolve(custody_ref)
        ok = (
            result.present == expected_present
            and result.effective_state == expected_state
            and result.authoritative_for_certification == expected_authoritative
        )
        print(
            ("ok   " if ok else "FAIL ")
            + "%s -> present=%s effective_state=%s authoritative=%s reason=%s"
            % (label, result.present, result.effective_state, result.authoritative_for_certification, result.reason)
        )
        if not ok:
            failures += 1

    with tempfile.TemporaryDirectory(prefix="website-evidence-custody-selftest-") as tmp:
        tmp_root = Path(tmp)

        missing_reconstruction_root = tmp_root / "missing-reconstruction"
        manifest = _minimal_custody_manifest(opaque_ref=opaque_ref, file_sha256=file_sha256)
        del manifest["custody"]["reconstruction"]
        _write_manifest(missing_reconstruction_root / manifest_relative, manifest)
        run_case(
            "i1. isolated manifest missing custody.reconstruction",
            missing_reconstruction_root, False, "custody_invalid", False,
        )

        missing_producer_root = tmp_root / "missing-produced-by-lane"
        manifest = _minimal_custody_manifest(opaque_ref=opaque_ref, file_sha256=file_sha256)
        del manifest["produced_by_lane"]
        _write_manifest(missing_producer_root / manifest_relative, manifest)
        run_case(
            "i2. isolated manifest missing produced_by_lane",
            missing_producer_root, False, "custody_invalid", False,
        )

        duplicate_root = tmp_root / "duplicate-contradictory"
        manifest_a = _minimal_custody_manifest(
            opaque_ref=opaque_ref, file_sha256=file_sha256, produced_by_lane="lane-a"
        )
        manifest_b = _minimal_custody_manifest(
            opaque_ref=opaque_ref, file_sha256=file_sha256, produced_by_lane="lane-b"
        )
        _write_manifest(duplicate_root / "qamus/task-packets/selftest-custody-manifest-a.json", manifest_a)
        _write_manifest(duplicate_root / "qamus/task-packets/selftest-custody-manifest-b.json", manifest_b)
        run_case(
            "j. duplicate contradictory manifest rows",
            duplicate_root, True, "contradictory", False,
        )

    return failures


def _focused_proof_remaining_schemes() -> int:
    """Pins the two-vote-artifact, cert-event, and dawahwiki-custody evidence
    scheme adapters against committed fixtures."""

    resolver = WebsiteEvidenceResolver(ROOT)
    failures = 0

    def check(
        label: str,
        reference: str,
        expected_present: bool,
        expected_state: str,
        expected_authoritative: bool,
    ) -> None:
        nonlocal failures
        result = resolver.resolve(reference)
        ok = (
            result.present == expected_present
            and result.effective_state == expected_state
            and result.authoritative_for_certification == expected_authoritative
        )
        print(
            ("ok   " if ok else "FAIL ")
            + "%s -> present=%s effective_state=%s authoritative=%s reason=%s"
            % (label, result.present, result.effective_state, result.authoritative_for_certification, result.reason)
        )
        if not ok:
            failures += 1

    # a. bound valid two-vote artifact -> certified_support / True
    check(
        "a. bound valid two-vote artifact",
        "two-vote-artifact:quran_2_34_5:p00slice-li-jarr",
        True, "certified_support", True,
    )

    # b. valid but unbound two-vote artifact -> review_verified / False
    check(
        "b. valid unbound two-vote artifact",
        "two-vote-artifact:quran_93_3_1:v11",
        True, "review_verified", False,
    )

    # c. nonexistent two-vote artifact -> evidence_unresolved / False
    check(
        "c. nonexistent two-vote artifact",
        "two-vote-artifact:quran_999_999_999:doesnotexist",
        False, "evidence_unresolved", False,
    )

    # d. current authoritative cert event -> certified / True
    check(
        "d. current cert event",
        "cert-event:101:fact:p00slice:2_34_5:seg",
        True, "certified", True,
    )

    # e. historical event whose fact is now review_required (later revoked
    #    by cert-event:166) -> review_required / False
    check(
        "e. historical now-review_required cert event",
        "cert-event:118:fact:p00slice:2_34_5:func",
        True, "review_required", False,
    )

    # f. nonexistent cert event -> evidence_unresolved / False
    check(
        "f. nonexistent cert event",
        "cert-event:999999:fact:selftest:nonexistent:0_0_0",
        False, "evidence_unresolved", False,
    )

    valid_custody_ref = (
        "dawahwiki:packets/p007-direct-source-w1/wave1-worklist.json"
        "#sha256:fb51c7de9c6951dc81015f754c1476481cd86339d577bcf6242d1d8158d604a2"
    )
    # g. valid manifested private-custody ref -> custody_verified / False
    check("g. valid custody ref", valid_custody_ref, True, "custody_verified", False)

    # h. same custody ref, wrong hash -> custody_hash_mismatch / False
    wrong_hash_ref = valid_custody_ref[:-1] + ("b" if valid_custody_ref[-1] != "b" else "c")
    check("h. custody ref with wrong hash", wrong_hash_ref, False, "custody_hash_mismatch", False)

    failures += _focused_proof_custody_manifest_integrity()

    # k. synthetic effective-state canaries: a revoked fact, and a certified
    #    fact whose dependency is invalidated -- both non-authoritative.
    revoked_state = {"fact:synth:revoked": {"status": "rejected", "fact": {}}}
    revoked_effective_state, revoked_authoritative, revoked_reason = effective_typed_fact_state(
        "fact:synth:revoked", revoked_state
    )
    ok = revoked_effective_state == "revoked" and not revoked_authoritative
    print(
        ("ok   " if ok else "FAIL ")
        + "k1. synthetic revoked fact -> effective_state=%s authoritative=%s reason=%s"
        % (revoked_effective_state, revoked_authoritative, revoked_reason)
    )
    if not ok:
        failures += 1

    invalidated_dependency_state = {
        "fact:synth:parent2": {
            "status": "certified",
            "fact": {"dependencies": {"fact_ids": ["fact:synth:child2"]}},
        },
        "fact:synth:child2": {"status": "blocked", "fact": {}},
    }
    invalidated_effective_state, invalidated_authoritative, invalidated_reason = effective_typed_fact_state(
        "fact:synth:parent2", invalidated_dependency_state
    )
    ok = invalidated_effective_state == "dependency_failed" and not invalidated_authoritative
    print(
        ("ok   " if ok else "FAIL ")
        + "k2. synthetic certified fact depending on invalidated fact -> "
        "effective_state=%s authoritative=%s reason=%s"
        % (invalidated_effective_state, invalidated_authoritative, invalidated_reason)
    )
    if not ok:
        failures += 1

    if failures:
        print("\n%d REMAINING-SCHEME PROOF CASE(S) FAILED" % failures)
        return 1
    print("\nALL REMAINING-SCHEME PROOF CASES PASSED")
    return 0


def _focused_proof() -> int:
    """Human-checkable proof for the six scenarios Round B must demonstrate."""

    resolver = WebsiteEvidenceResolver(ROOT)
    failures = 0

    def check(label: str, reference: str, expected_state: str, expected_authoritative: bool) -> None:
        nonlocal failures
        result = resolver.resolve(reference)
        ok = (
            result.effective_state == expected_state
            and result.authoritative_for_certification == expected_authoritative
        )
        print(
            ("ok   " if ok else "FAIL ")
            + "%s -> effective_state=%s authoritative=%s reason=%s"
            % (label, result.effective_state, result.authoritative_for_certification, result.reason)
        )
        if not ok:
            failures += 1

    check("1. certified typed fact", "fact:p00slice:2_34_5:seg", "certified", True)
    check("2. superseded typed fact", "fact:p00slice:2_34_5:func", "review_required", False)
    check(
        "3. nonexistent fact",
        "fact:selftest:sha256:" + "0" * 64,
        "evidence_unresolved",
        False,
    )
    check(
        "4. proofp candidate fact",
        "fact:proofp:sha256:"
        "4c3881c19eb21b0b363e688682650178e5348dc4e3dbc9b7756a9a32c2dbb6f6",
        "candidate",
        False,
    )
    check("5. invented scheme", "invented-scheme:selftest:1", "unsupported_scheme", False)

    synthetic_state = {
        "fact:synth:parent": {
            "status": "certified",
            "fact": {"dependencies": {"fact_ids": ["fact:synth:child"]}},
        },
        "fact:synth:child": {"status": "review_required", "fact": {}},
    }
    synthetic_effective_state, synthetic_authoritative, synthetic_reason = effective_typed_fact_state(
        "fact:synth:parent", synthetic_state
    )
    ok = synthetic_effective_state == "dependency_failed" and not synthetic_authoritative
    print(
        ("ok   " if ok else "FAIL ")
        + "6. synthetic certified fact depending on review_required fact -> "
        "effective_state=%s authoritative=%s reason=%s"
        % (synthetic_effective_state, synthetic_authoritative, synthetic_reason)
    )
    if not ok:
        failures += 1

    if failures:
        print("\n%d FOCUSED PROOF CASE(S) FAILED" % failures)
        return 1
    print("\nALL FOCUSED PROOF CASES PASSED")
    return 0


if __name__ == "__main__":
    base_exit = _focused_proof()
    integrity_exit = _focused_proof_authority_integrity()
    remaining_schemes_exit = _focused_proof_remaining_schemes()
    sys.exit(base_exit or integrity_exit or remaining_schemes_exit)
