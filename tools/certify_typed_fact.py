#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fact-level certification transition engine for typed-claim facts (stdlib only).

Ports the fact-ledger discipline (tools/fact_ledger.py token-layer state machine)
to the typed-claim plane governed by docs/certification-authority.md:

* transitions: candidate -> review_required -> certified, plus blocked (defeater)
  and rejected; revocation drops certified -> review_required (doc section 5);
* certification requires the reconstructible evidence bundle of doc section 3
  (exact source addresses, exactly one verbatim quotation or structured source
  fact, ladder-consistent evidence_mode, dependencies, derivation chain, conflict
  record, reviewer artifacts where the rung demands them, and invalidation
  conditions so revocation can propagate);
* ladder semantics: ``deterministic_derivation_from_certified_facts`` and
  ``paired_form_inference`` certify only when every input fact is itself
  currently certified (a derivation cannot outrank its weakest input);
  ``cross_source_corroboration`` requires at least two source addresses from
  distinct source families; two-vote fact types certify only against a
  ``tools/validate_two_vote_artifacts.py``-passing bundle (the artifact is
  consumed, never re-derived inline);
* every transition appends one event to an append-only, hash-chained
  certification event trail (jsonl) with actor, evidence-bundle reference and
  timestamp; gaps and tampering fail closed;
* ``revoke()`` walks the reverse dependency index (derivation_chain input ids,
  dependencies.fact_ids, dependent_fact_ids) and mechanically flags every
  dependent fact to review_required; deterministic/paired derivations from a
  revoked input are automatically de-certified.

No live surface is read or mutated. The committed sufaha packet demo is
read-only over the committed contract: it refuses certification for every fact
of the ten non-two-vote typed-claim families, because the MCP verbatim evidence
file their family contract declares (``sufaha-evidence.jsonl``) is not committed
in-repo — and it stays refused even when a temp packet makes that address
resolvable, since family authority is the committed contract's evidence, not a
citation string. Only ``governor_relation`` certifies there, against the
validated two-vote artifact. The full transition + revocation cascade is
exercised by ``--self-test`` over a fact type with a registered producer
contract, so no family name is ever borrowed to make a fixture green.
"""

from __future__ import annotations

import argparse
import copy
import functools
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import validate_two_vote_artifacts as two_vote  # noqa: E402
from tools.typed_claim_contract import (  # noqa: E402
    DERIVED_EVIDENCE_MODES,
    EVIDENCE_MODES,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

EVENT_SCHEMA = "qamus.certification_event.v1"
EVENTS_NAME = "events.jsonl"
GENESIS = "genesis"

# Default in-repo store for the typed-fact certification event trail. It does
# not exist today (zero facts are certified at the typed-claim layer); readers
# such as build_vn_readiness_v2 must treat an absent store as a zero count.
DEFAULT_STORE_DIR = ROOT / "qamus" / "certification" / "typed-fact-store"

CERT_TRANSITIONS = {
    "candidate": {"review_required", "blocked", "rejected"},
    "pending": {"review_required", "blocked"},
    "review_required": {"certified", "rejected", "blocked"},
    # certified -> review_required is the revocation drop (doc section 5.1/5.2);
    # certified -> blocked is a defeater firing (doc section 5.3).
    "certified": {"review_required", "blocked"},
    "blocked": set(),
    "rejected": set(),
}

# Ladder rung 4 (doc section 2): i'rab-bearing conclusions that surface to a
# learner certify only behind a reconstructible two-vote artifact bundle.
TWO_VOTE_FACT_TYPES = {
    "governor_relation",
    "case_mood_governor",
    "contextual_function",
    "irab_rendering",
}

# Certification is a POSITIVE act: it requires a contract that says what evidence
# this class of fact needs. A fact type is certifiable only if it is either
# produced by a registered projector (whose gate then applies) or listed here as a
# typed-claim family this plane already knows how to gate. Anything else has no
# contract at all, so relabelling a gated fact's type/projector/producer sheds the
# gate INTO refusal, never out of it. Extending this list is a deliberate edit.
#
# Membership here is NECESSARY BUT NEVER SUFFICIENT: a fact-type string is not a
# credential. A recognised family that resolves NO registered projector gate must
# additionally satisfy the authority its own family actually has --
#
#   * two-vote families certify only against a validated two-vote artifact naming
#     the fact (see ``two_vote_refusal``), which is external evidence, not a name;
#   * every other recognised family must establish membership against the committed
#     contract that declares it: the exact declared review-artifact citation, on the
#     carrier that is actually resolved, plus the declared producer and projector,
#     plus an evidence file committed in this repository (see
#     ``family_authority_refusal``). A citation string is not evidence until it
#     opens onto something.
#
# So a foreign payload relabelled into a recognised family cannot borrow that
# family's authority from the fact_type field, and cannot mint it from an address
# nothing resolves.
RECOGNISED_TYPED_CLAIM_FACT_TYPES = frozenset(TWO_VOTE_FACT_TYPES) | frozenset({
    # proof-noun-sufaha typed-claim families (qamus/examples/proof-noun-sufaha/)
    "case_ending",
    "paired_y_removal",
    "plural_formation",
    "plural_introduced_letters",
    "plural_lexical_body",
    "plural_pattern",
    "retained_radicals",
    "root",
    "singular_pattern",
    "singular_plural_relation",
})

ADJUDICATION_EVIDENCE_PREFIX = "adjudication:"
SUFAHA_CONTRACT = ROOT / "qamus" / "examples" / "proof-noun-sufaha" / "sufaha-contract.json"
TWO_VOTE_SAMPLE = ROOT / "qamus" / "examples" / "two_vote_artifact.sample.jsonl"


NEVER_AUTO_RESOLVE = "never_auto_resolve"


class CertificationError(ValueError):
    """Raised when a transition, bundle, or event trail fails closed validation."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


FAMILY_CONTRACT_ARTIFACTS = (
    ROOT / "qamus" / "examples" / "proof-noun-sufaha" / "sufaha-contract.json",
)


# A family anchor is only ever read from the SAME carrier the review-artifact
# reconstructibility check reads (``source_evidence.source_addresses`` and
# ``source_address``) and only with this source kind. An address that appears only
# under ``dependencies.source_addresses``, or under any other source kind, is never
# resolved against a packet, so it can claim anything and authorizes nothing.
FAMILY_ANCHOR_SOURCE_KIND = "review_artifact"


# Fields the certification STATE MACHINE owns, and only those. Everything else in
# a fact is truth-bearing and is bound by ``family_body_digest``: fact_type,
# fact_value, evidence_mode, source_evidence (addresses, quotation or structured
# source fact), source_address, dependencies, derivation_chain, evidence identity,
# contradiction records, defeaters/guards, producer, rule_projector, occurrence and
# surface spans, and any other key a contract carries.
#
#   * ``certification`` — the status/reason the store itself writes;
#   * ``unresolved_blockers`` — review bookkeeping, cleared as blockers are closed;
#   * ``dependent_fact_ids`` / ``dependent_projection_ids`` — back-references that
#     grow as OTHER facts register against this one, so they cannot be fixed at
#     declaration time.
#
# Nothing else may be excluded: an exclusion is a field a forger may rewrite.
FAMILY_BODY_STATE_FIELDS = frozenset({
    "certification",
    "unresolved_blockers",
    "dependent_fact_ids",
    "dependent_projection_ids",
})


def family_body_digest(fact: Dict[str, Any]) -> str:
    """A deterministic digest of everything in a fact except state-machine fields."""

    body = {key: value for key, value in (fact or {}).items()
            if key not in FAMILY_BODY_STATE_FIELDS}
    return _sha256(_canonical(body))


def family_body_difference(candidate: Dict[str, Any], declared: Dict[str, Any]) -> List[str]:
    """The truth-bearing keys on which a candidate differs from its declaration."""

    keys = (set(candidate or {}) | set(declared or {})) - FAMILY_BODY_STATE_FIELDS
    return sorted(
        key for key in keys
        if _canonical((candidate or {}).get(key)) != _canonical((declared or {}).get(key))
    )


def _build_family_index(payload: Dict[str, Any], path: Path) -> Dict[str, Dict[str, Any]]:
    """Index one committed family contract by declared fact type.

    Each citation maps to the ONE declaring fact it addresses — its id, producer,
    projector, evidence mode, body digest and the declared body itself — so family
    authority is never a type-wide set a foreign payload can satisfy.
    """

    index: Dict[str, Dict[str, Any]] = {}
    contract_id = str(payload.get("contract_id") or "")
    for fact in payload.get("facts") or []:
        if not isinstance(fact, dict):
            continue
        fact_type = str(fact.get("fact_type") or "")
        anchor = fact.get("source_address")
        if not isinstance(anchor, dict):
            continue
        address = str(anchor.get("address") or "")
        if not fact_type or not address:
            continue
        if str(anchor.get("source_kind") or "") != FAMILY_ANCHOR_SOURCE_KIND:
            # Only a reconstructible review artifact can anchor a family.
            continue
        declared = index.setdefault(fact_type, {
            "contract_path": path,
            "contract_id": contract_id,
            "citations": {},
        })
        declared["citations"][address] = {
            "fact_id": str(fact.get("fact_id") or ""),
            "producer": str(((fact.get("producer") or {}).get("id")) or ""),
            "projector": str(((fact.get("rule_projector") or {}).get("projector_id")) or ""),
            "evidence_mode": str(fact.get("evidence_mode") or ""),
            "body_digest": family_body_digest(fact),
            "body": copy.deepcopy(fact),
        }
    return index


@functools.lru_cache(maxsize=1)
def family_contract_index() -> Dict[str, Dict[str, Any]]:
    """Per declared family, the exact facts its committed family contract declares.

    Read out of the committed contracts rather than hard-coded here, so a family's
    permitted authority cannot drift away from the artifact that defines it.
    """

    index: Dict[str, Dict[str, Any]] = {}
    for path in FAMILY_CONTRACT_ARTIFACTS:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):  # a damaged contract declares nothing
            continue
        for fact_type, declared in _build_family_index(payload, path).items():
            index.setdefault(fact_type, declared)["citations"].update(declared["citations"])
    return index


def _family_anchor_candidates(fact: Dict[str, Any]) -> List[str]:
    """Addresses offered on the reconstructible carrier, with the anchor kind.

    ``dependencies.source_addresses`` is deliberately excluded: the review-artifact
    reconstructibility check never reads it, so an address living only there is
    never opened and cannot be evidence of anything.
    """

    items: List[Any] = list(_addresses(fact))
    primary = fact.get("source_address")
    if isinstance(primary, dict):
        items.append(primary)
    return [
        str(item["address"]) for item in items
        if isinstance(item, dict) and item.get("address")
        and str(item.get("source_kind") or "") == FAMILY_ANCHOR_SOURCE_KIND
    ]


def family_evidence_path(declared: Dict[str, Any], address: str) -> Optional[Path]:
    """The in-repository path a declared citation resolves to, or None if unsafe.

    Resolution is relative to the DECLARING contract's own directory and must stay
    inside the repository: a citation may not escape into the filesystem, and a
    lookalike path is not the declared artifact.
    """

    file_part = str(address).split("#", 1)[0]
    if (not file_part or os.path.isabs(file_part)
            or file_part.startswith(("/", "\\")) or ".." in file_part):
        return None
    candidate = Path(declared["contract_path"]).parent / file_part
    try:
        candidate.resolve().relative_to(ROOT.resolve())
    except (OSError, ValueError):
        return None
    return candidate


def repository_blob_refusal(path: Path, *, repo_root: Path = ROOT) -> Optional[str]:
    """Refusal unless repository authority proves this path is committed, unchanged.

    Existence in a worktree proves nothing: anyone can drop a file next to a
    contract. The path must be tracked at the CURRENT commit and its working-tree
    content must equal that committed blob. If repository authority cannot be
    consulted at all, that is a refusal too — never an assumption of good faith.
    """

    root = Path(repo_root).resolve()
    try:
        relative = Path(path).resolve().relative_to(root)
    except (OSError, ValueError):
        return "%s is outside the repository, so it can never be committed evidence" % path
    rel = relative.as_posix()

    def git(*args: str) -> Optional[subprocess.CompletedProcess]:
        try:
            return subprocess.run(("git", "-C", str(root)) + args,
                                  capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return None

    tracked = git("rev-parse", "--verify", "--quiet", "HEAD:%s" % rel)
    if tracked is None:
        return ("repository authority is unavailable, so %s cannot be shown to be committed "
                "evidence; certification fails closed" % rel)
    if tracked.returncode != 0 or not tracked.stdout.strip():
        return ("%s exists in the working tree but is not tracked at the current commit; "
                "an untracked lookalike is not committed evidence" % rel)
    unchanged = git("diff", "--quiet", "HEAD", "--", rel)
    if unchanged is None or unchanged.returncode not in (0, 1):
        return ("repository authority could not compare %s against the commit, so it cannot be "
                "accepted as committed evidence" % rel)
    if unchanged.returncode == 1:
        return ("%s has drifted from the blob committed at %s; the evidence a citation opens "
                "must be the committed bytes, not the working copy"
                % (rel, tracked.stdout.strip()[:12]))
    return None


def _record_carries(record: Any, represented: str) -> bool:
    """Whether an opened evidence record actually carries this verbatim evidence.

    The comparison walks the record's own values rather than its serialisation: a
    quotation legitimately contains quotes and braces, and an escaped-JSON substring
    test would reject exactly the verbatim material it is meant to confirm.
    """

    if isinstance(record, str):
        return represented == record or represented in record
    if isinstance(record, dict):
        return (_canonical(record) == represented
                or any(_record_carries(value, represented) for value in record.values()))
    if isinstance(record, list):
        return (_canonical(record) == represented
                or any(_record_carries(value, represented) for value in record))
    return False


def evidence_fragment_refusal(evidence_path: Path, address: str,
                              fact: Dict[str, Any]) -> Optional[str]:
    """Refusal unless the cited fragment opens and corroborates this exact fact.

    ``#fact=N`` selects the N-th record of the cited artifact (one JSON object per
    line for ``.jsonl``, or the N-th entry of a ``facts`` array / top-level array
    for ``.json``). That record must carry this fact's verbatim quotation, and must
    not name a different fact type. A fragment nothing can open is not evidence.
    """

    fragment = address.split("#", 1)[1] if "#" in address else ""
    if not fragment.startswith("fact=") or not fragment[len("fact="):].isdigit():
        return ("the citation %r carries no resolvable record fragment, so nothing in %s can be "
                "opened to corroborate this fact" % (address, evidence_path.name))
    index = int(fragment[len("fact="):])
    try:
        text = evidence_path.read_text(encoding="utf-8")
    except (OSError, ValueError) as error:
        return "the cited evidence %s could not be opened (%s)" % (evidence_path.name, error)
    records: List[Any] = []
    try:
        if evidence_path.suffix == ".jsonl":
            records = [json.loads(line) for line in text.splitlines() if line.strip()]
        else:
            payload = json.loads(text)
            if isinstance(payload, dict):
                records = list(payload.get("facts") or [])
            elif isinstance(payload, list):
                records = list(payload)
    except ValueError as error:
        return "the cited evidence %s is not a readable record artifact (%s)" % (
            evidence_path.name, error)
    if not records or not 1 <= index <= len(records):
        return ("the citation %r addresses record %d of %s, which holds %d record(s); the cited "
                "fragment does not exist" % (address, index, evidence_path.name, len(records)))
    record = records[index - 1]
    source_evidence = fact.get("source_evidence") or {}
    quotation = source_evidence.get("source_quotation")
    represented = quotation if isinstance(quotation, str) and quotation else None
    if represented is None:
        structured = source_evidence.get("structured_source_fact")
        represented = _canonical(structured) if structured is not None else None
    if represented is None:
        return ("this fact carries neither a verbatim quotation nor a structured source fact, so "
                "the cited record %r cannot corroborate it" % address)
    if not _record_carries(record, represented):
        return ("the record at %r does not carry this fact's verbatim evidence, so the citation "
                "does not corroborate the claim being certified" % address)
    record_type = str(record.get("fact_type") or "") if isinstance(record, dict) else ""
    if record_type and record_type != str(fact.get("fact_type") or ""):
        return ("the record at %r is evidence for %r, not for %r"
                % (address, record_type, fact.get("fact_type")))
    return None


def family_authority_refusal(fact: Dict[str, Any], *,
                             contract_id: Optional[str] = None) -> Optional[str]:
    """Refusal when a recognised-but-ungated family's authority is not established.

    A registered projector gate already decides what a fact needs. Where no such
    gate exists, the family name is only a word; the fact must be tied to the
    committed contract that declares the family by

    1. citing that contract's own review-artifact address for a fact of THIS type,
       on the carrier the reconstructibility check actually reads;
    2. carrying the producer, projector and evidence mode THAT CITATION's declaring
       fact carries — never a type-wide set, and never an omitted field;
    3. presenting the declared body itself: every truth-bearing field is digest-
       compared against the declaration (see ``FAMILY_BODY_STATE_FIELDS`` for the
       narrow set of state-machine fields excluded), so a declared fact id can never
       carry a substituted fact_value, quotation, dependency or derivation;
    4. opening onto evidence that repository authority proves is tracked at the
       current commit and byte-identical to that commit, whose cited fragment
       actually corroborates this fact.

    Anything less would let a relabelled payload assert its own family membership.
    """

    fact_type = str(fact.get("fact_type") or "")
    declared = family_contract_index().get(fact_type)
    if not declared:
        return (
            "fact_type %r resolves no registered projector gate and no committed family contract "
            "declares it; a fact-type name can never by itself authorize certification" % fact_type
        )
    contract_display = Path(declared["contract_path"]).relative_to(ROOT).as_posix()
    citations = declared["citations"]

    offered = _family_anchor_candidates(fact)
    if not offered:
        return (
            "fact_type %r resolves no registered projector gate, so its family membership must be "
            "anchored to %s by a %r source address in source_evidence.source_addresses or "
            "source_address; this fact offers none (a dependency-only or differently-kinded "
            "address is never resolved, so it is not evidence)"
            % (fact_type, contract_display, FAMILY_ANCHOR_SOURCE_KIND)
        )
    cited = sorted(address for address in offered if address in citations)
    if not cited:
        return (
            "fact_type %r must cite the exact %s address that contract declares for a %s fact "
            "(one of: %s); it cites %s, so its family membership is an unverified relabelling"
            % (fact_type, contract_display, fact_type,
               ", ".join(sorted(citations)), ", ".join(sorted(offered)))
        )
    declaring = {citations[address]["fact_id"] for address in cited}
    if len(declaring) > 1:
        return (
            "the citations %s are declared by different %s facts (%s); one fact may not present "
            "another's evidence" % (", ".join(cited), contract_display, ", ".join(sorted(declaring)))
        )
    declared_fact = citations[cited[0]]

    # The declared fact, not a type-wide set: producer, projector and evidence mode
    # are the ones THIS citation's declaring fact carries.
    producer = str(((fact.get("producer") or {}).get("id")) or "")
    if producer != declared_fact["producer"]:
        return (
            "the citation %r is declared by %s with producer %r; this fact declares %s, so it is "
            "not a fact of that family"
            % (cited[0], contract_display, declared_fact["producer"],
               repr(producer) if producer else "no producer")
        )
    projector = str(((fact.get("rule_projector") or {}).get("projector_id")) or "")
    if projector != declared_fact["projector"]:
        return (
            "the citation %r is declared by %s with projector %r; this fact declares %s, so it is "
            "not a fact of that family"
            % (cited[0], contract_display, declared_fact["projector"],
               repr(projector) if projector else "no projector")
        )
    if (contract_id is not None and declared["contract_id"]
            and str(contract_id) != declared["contract_id"]):
        return (
            "fact_type %r is declared by %s under contract_id %r; this fact is registered under "
            "%r, so the citation does not belong to it"
            % (fact_type, contract_display, declared["contract_id"], str(contract_id))
        )
    if declared_fact["fact_id"] and str(fact.get("fact_id") or "") != declared_fact["fact_id"]:
        return (
            "the citation %r identifies the %s fact %s declared by %s; this payload presents "
            "fact_id %r, so it is not the fact that citation declares"
            % (cited[0], fact_type, declared_fact["fact_id"], contract_display,
               str(fact.get("fact_id") or ""))
        )
    if str(fact.get("evidence_mode") or "") != declared_fact["evidence_mode"]:
        return (
            "the citation %r is declared at evidence_mode %r; this fact claims %r, and a fact may "
            "not certify on a rung its declaration never claimed"
            % (cited[0], declared_fact["evidence_mode"], str(fact.get("evidence_mode") or ""))
        )

    # A fact_id is a label. What certification asserts is the BODY, so the body must
    # be the declared one: every truth-bearing field, digest-compared.
    if family_body_digest(fact) != declared_fact["body_digest"]:
        differing = family_body_difference(fact, declared_fact["body"])
        return (
            "this payload differs from the %s fact %s declared by %s on %s; a declared fact id "
            "may not carry a substituted body"
            % (fact_type, declared_fact["fact_id"], contract_display,
               ", ".join(differing) or "an excluded field")
        )

    # The citation must open onto committed evidence. While the declared evidence is
    # absent from the repository, no fact of this family can be certified — that is
    # the honest state, not a reason to accept the citation as its own proof.
    evidence_path = family_evidence_path(declared, cited[0])
    if evidence_path is None:
        return (
            "the family citation %r does not resolve to a repository-relative path under %s"
            % (cited[0], contract_display)
        )
    if not evidence_path.exists():
        return (
            "%s declares the evidence for %r at %s, which is not committed in-repo; "
            "no fact of this family can be certified until that evidence is committed"
            % (contract_display, fact_type, evidence_path.relative_to(ROOT).as_posix())
        )
    blob_refusal = repository_blob_refusal(evidence_path)
    if blob_refusal is not None:
        return blob_refusal
    return evidence_fragment_refusal(evidence_path, cited[0], fact)


def _gate_rank(tier):
    if tier is None:
        return -1
    try:
        from tools import fact_projectors
    except Exception:  # pragma: no cover
        return -1
    return fact_projectors.load_gate_tiers().get(tier, {}).get("rank", 0)


def producing_projector_gate(fact: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], str]:
    """Resolve the PRODUCING projector gate tier from repository authority.

    The fact's own claimed tier is never trusted, and a projector id can never
    shed the gate its fact TYPE carries. Both bindings are resolved:

    * projector-bound: ``rule_projector.projector_id`` must be registered AND its
      contract must actually produce ``fact.fact_type``; a registered projector
      that produces something else is an incoherent claim, not a weaker gate;
    * type-bound: the strictest registered gate for ``fact.fact_type``.

    The two must agree on producer identity, and the STRICTEST valid gate wins.
    """

    try:
        from tools import fact_projectors
    except Exception as error:  # pragma: no cover - registry must be importable
        raise CertificationError("cannot resolve the producing projector registry: %s" % error)

    fact_type = str(fact.get("fact_type") or "")
    projector_id = ((fact.get("rule_projector") or {}).get("projector_id"))
    type_tier = fact_projectors.REGISTRY.gate_tier_for_output_fact_type(fact_type) if fact_type else None

    projector_tier = None
    if projector_id:
        try:
            contract = fact_projectors.REGISTRY.contract(str(projector_id))
        except fact_projectors.ProjectorValidationError:
            contract = None
        if contract is not None:
            if contract.get("output_fact_type") != fact_type:
                return (
                    type_tier,
                    str(projector_id),
                    "projector/fact_type mismatch: %s produces %s, not %s"
                    % (projector_id, contract.get("output_fact_type"), fact_type),
                )
            projector_tier = contract.get("gate_tier")

    if projector_tier is None and type_tier is None:
        return None, (str(projector_id) if projector_id else None), "no registered producer"
    strictest = max(
        [tier for tier in (projector_tier, type_tier) if tier is not None],
        key=_gate_rank,
    )
    basis = "registered projector_id" if projector_tier is not None else "registered output_fact_type"
    if projector_tier is not None and type_tier is not None and projector_tier != type_tier:
        basis = "strictest of projector and fact-type gates"
    return strictest, (str(projector_id) if projector_id else None), basis


def gate_refusal(fact: Dict[str, Any], *, contract_id: Optional[str] = None) -> Optional[str]:
    """Refusal reason when the producing projector may never reach certified."""

    tier, projector_id, basis = producing_projector_gate(fact)
    if basis.startswith("projector/fact_type mismatch"):
        return (
            "the fact names a registered projector that does not produce its fact type (%s); "
            "a projector identity may never shed a fact-type gate" % basis
        )
    if tier == NEVER_AUTO_RESOLVE:
        return (
            "the producing projector is gated %s (%s: %s); the gate SSOT rejects this class outright, "
            "so no evidence bundle, dependency or vote can certify it"
            % (NEVER_AUTO_RESOLVE, basis, projector_id or fact.get("fact_type"))
        )
    fact_type = str(fact.get("fact_type") or "")
    if tier is None:
        if fact_type not in RECOGNISED_TYPED_CLAIM_FACT_TYPES:
            # No registered producer AND no recognised typed-claim family: this fact
            # has no contract deciding what evidence it needs, so it can never be
            # certified.
            return (
                "no registered producer gate and no recognised typed-claim contract for fact_type %r "
                "/ projector %r; an unrecognised producer can never be certified"
                % (fact.get("fact_type"), projector_id)
            )
        if fact_type not in TWO_VOTE_FACT_TYPES:
            # Recognised but ungated: the family name proves nothing on its own, so
            # the fact must establish its membership against the contract that
            # declares the family — a cited, resolvable, committed artifact plus the
            # declared producer and projector identity. (Two-vote families are
            # already bound to a validated vote artifact.)
            return family_authority_refusal(fact, contract_id=contract_id)
    return None


def identity_refusal(fact: Dict[str, Any]) -> Optional[str]:
    """Refusal when a content-addressed fact id no longer matches its content."""

    try:
        from tools import fact_projectors
    except Exception:  # pragma: no cover
        return None
    recomputer = fact_projectors.identity_recomputer_for(fact)
    if recomputer is None:
        return None
    try:
        expected = recomputer(fact)
    except Exception as error:  # noqa: BLE001
        return "the producing projector could not recompute this fact id: %s" % error
    if expected != fact.get("fact_id"):
        return (
            "content-addressed fact id does not match its content: a changed projector, fact type "
            "or semantic claim may not retain the original fact_id"
        )
    return None


def _addresses(fact: Dict[str, Any]) -> List[Dict[str, Any]]:
    source_evidence = fact.get("source_evidence") or {}
    addresses = source_evidence.get("source_addresses")
    return [item for item in addresses if isinstance(item, dict)] if isinstance(addresses, list) else []


def _derivation_input_ids(fact: Dict[str, Any]) -> List[str]:
    seen: List[str] = []
    for step in fact.get("derivation_chain") or []:
        if not isinstance(step, dict):
            continue
        for input_id in step.get("input_fact_ids", []) or []:
            if input_id not in seen:
                seen.append(input_id)
    return seen


def load_two_vote_row(bundle_path: os.PathLike[str] | str,
                      artifact_id: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Consume a two-vote artifact bundle via its own validator (never re-derive).

    The whole bundle must pass ``tools/validate_two_vote_artifacts.validate``;
    the named artifact must exist and be ``two_vote_verified``.
    """

    errors: List[str] = []
    path = str(bundle_path)
    if not os.path.exists(path):
        return None, ["two-vote bundle does not exist: %s" % path]
    count, bundle_errors = two_vote.validate(path)
    if bundle_errors:
        errors.append(
            "two-vote bundle fails validate_two_vote_artifacts (%d row(s)): %s"
            % (count, "; ".join(bundle_errors[:3]))
        )
        return None, errors
    row = None
    for _line_no, candidate in two_vote.iter_jsonl(path):
        if isinstance(candidate, dict) and candidate.get("artifact_id") == artifact_id:
            row = candidate
            break
    if row is None:
        return None, ["two-vote bundle has no artifact %s" % artifact_id]
    if row.get("claim_state") != "two_vote_verified":
        errors.append(
            "two-vote artifact %s is %s, not two_vote_verified"
            % (artifact_id, row.get("claim_state"))
        )
        return None, errors
    return row, errors


def evidence_bundle_errors(fact: Dict[str, Any],
                           status_by_id: Dict[str, str],
                           *,
                           two_vote_row: Optional[Dict[str, Any]] = None,
                           packet_dir: os.PathLike[str] | str | None = None) -> List[str]:
    """Return every doc-section-3 reason this fact may NOT be certified."""

    errors: List[str] = []
    fact_id = fact.get("fact_id") or "<missing fact_id>"

    def err(message: str) -> None:
        errors.append("%s: %s" % (fact_id, message))

    mode = fact.get("evidence_mode")
    if mode not in EVIDENCE_MODES:
        err("evidence_mode %r is not a closed contract value" % (mode,))
        return errors
    if mode == "unresolved":
        err("unresolved evidence may never carry certification.status certified")
        return errors

    # 1-2. Exact source address(es) + exactly one verbatim quotation or
    # structured source fact (source_evidence oneOf).
    source_evidence = fact.get("source_evidence")
    if not isinstance(source_evidence, dict):
        err("certification requires a source_evidence bundle (missing)")
        return errors
    addresses = _addresses(fact)
    if not addresses or any(not item.get("address") for item in addresses):
        err("source_evidence requires at least one exact source address")
    representations = [
        key for key in ("source_quotation", "structured_source_fact") if key in source_evidence
    ]
    if len(representations) != 1:
        err("source_evidence must carry exactly one verbatim quotation or structured source fact")

    # Review-artifact addresses must be reconstructible from committed files.
    for item in addresses + [fact.get("source_address") or {}]:
        if item.get("source_kind") != "review_artifact":
            continue
        address = str(item.get("address") or "")
        file_part = address.split("#", 1)[0]
        if not file_part:
            err("review-artifact address is empty")
            continue
        if packet_dir is None:
            err("review-artifact evidence %s cannot be resolved without a packet directory" % file_part)
            continue
        if os.path.isabs(file_part) or file_part.startswith(("/", "\\")) or ".." in file_part:
            err("review-artifact address %s must be packet-relative" % file_part)
            continue
        if not (Path(packet_dir) / file_part).exists():
            err("review-artifact evidence %s is not committed in-repo under the packet" % file_part)

    # 4. Dependencies actually relied upon.
    dependencies = fact.get("dependencies")
    if not isinstance(dependencies, dict):
        err("certification requires a dependencies record")
        dependencies = {}
    dependency_ids = dependencies.get("fact_ids") or []

    # 5 + ladder. Derivational/inferential modes need a re-runnable chain whose
    # every input is itself currently certified (FAM4/FAM5 overstatement closure).
    input_ids = _derivation_input_ids(fact)
    if mode in DERIVED_EVIDENCE_MODES:
        if not fact.get("derivation_chain"):
            err("%s requires a non-empty derivation_chain" % mode)
        if not input_ids:
            err("%s requires derivation input fact ids" % mode)
        for input_id in input_ids:
            if input_id not in dependency_ids:
                err("derivation input %s is not listed in dependencies.fact_ids" % input_id)
            state = status_by_id.get(input_id)
            if state is None:
                err("%s requires registered input fact %s" % (mode, input_id))
            elif state != "certified":
                err(
                    "%s requires every input fact to be certified; %s is %s"
                    % (mode, input_id, state)
                )

    # Ladder: corroboration means independent source families, not repetition.
    if mode == "cross_source_corroboration":
        families = {item.get("source_kind") for item in addresses if item.get("address")}
        if len(addresses) < 2 or len(families) < 2:
            err(
                "cross_source_corroboration requires at least two source addresses "
                "from distinct source families (found %d address(es), %d family(ies))"
                % (len(addresses), len(families))
            )

    # Ladder rung 5: adjudication needs the reviewer artifact reference.
    if mode == "owner_or_scholar_adjudication":
        evidence_ids = (fact.get("evidence") or {}).get("evidence_ids") or []
        if not any(str(item).startswith(ADJUDICATION_EVIDENCE_PREFIX) for item in evidence_ids):
            err(
                "owner_or_scholar_adjudication requires an adjudication artifact id "
                "(%s...) in evidence.evidence_ids" % ADJUDICATION_EVIDENCE_PREFIX
            )

    # Ladder rung 4: two-vote fact types consume the artifact bundle.
    if fact.get("fact_type") in TWO_VOTE_FACT_TYPES:
        if two_vote_row is None:
            err(
                "fact_type %s sits on the two-vote rung and requires a "
                "validate_two_vote_artifacts-passing bundle reference" % fact.get("fact_type")
            )
        else:
            bundle_loc = (two_vote_row.get("occurrence") or {}).get("quran_loc")
            fact_locs = {item.get("address") for item in addresses}
            if bundle_loc not in fact_locs:
                err(
                    "two-vote artifact occurrence %s is not among the fact's "
                    "source addresses" % bundle_loc
                )

    # 6. Conflict record must exist (possibly empty) — certifying over an
    # unattached known conflict is a violation; attachment is representable.
    if not isinstance(fact.get("contradiction_records"), list):
        err("certification requires a contradiction/tension conflict record (list, may be empty)")

    # 8. Invalidation conditions so revocation can propagate.
    if not isinstance(fact.get("defeaters"), list):
        err("certification requires a defeaters list (may be empty)")
    dependent_facts = fact.get("dependent_fact_ids")
    dependent_projections = fact.get("dependent_projection_ids")
    if not isinstance(dependent_facts, list) or not isinstance(dependent_projections, list):
        err("certification requires dependent_fact_ids and dependent_projection_ids lists")
    elif not dependent_facts and not dependent_projections:
        err("certification requires at least one dependent fact or projection id so revocation can propagate")
    return errors


class TypedFactCertificationStore:
    """Append-only, hash-chained certification event trail for typed facts."""

    def __init__(self, directory: os.PathLike[str] | str):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.events_path = self.directory / EVENTS_NAME

    # -- event trail primitives -------------------------------------------
    def _events(self) -> List[Dict[str, Any]]:
        if not self.events_path.exists():
            return []
        events: List[Dict[str, Any]] = []
        with self.events_path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    raise CertificationError("blank event trail line %d" % number)
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise CertificationError(
                        "invalid JSON on event trail line %d: %s" % (number, exc)
                    ) from exc
        return events

    def _append_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        events = self._events()
        event = copy.deepcopy(event)
        event["schema"] = EVENT_SCHEMA
        event["seq"] = len(events) + 1
        event["prev_event_sha256"] = (
            _sha256(_canonical(events[-1])) if events else GENESIS
        )
        event["event_id"] = "cert-event:%d:%s" % (event["seq"], event.get("fact_id", ""))
        with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical(event) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return event

    # -- folded state ------------------------------------------------------
    def state(self) -> Dict[str, Dict[str, Any]]:
        state: Dict[str, Dict[str, Any]] = {}
        for event in self._events():
            fact_id = event.get("fact_id")
            if event.get("event_type") == "register":
                state[fact_id] = {
                    "status": event.get("to_status"),
                    "fact": event.get("fact"),
                    "contract_id": event.get("contract_id"),
                }
            elif fact_id in state:
                state[fact_id]["status"] = event.get("to_status")
        return state

    def status_by_id(self) -> Dict[str, str]:
        return {fact_id: entry["status"] for fact_id, entry in self.state().items()}

    def certified_fact_ids(self) -> List[str]:
        return sorted(
            fact_id for fact_id, status in self.status_by_id().items() if status == "certified"
        )

    # -- transitions -------------------------------------------------------
    def register(self, fact: Dict[str, Any], *, contract_id: str, actor: str,
                 timestamp: str) -> Dict[str, Any]:
        fact_id = fact.get("fact_id")
        if not fact_id:
            raise CertificationError("a registered fact requires a fact_id")
        stale = identity_refusal(fact)
        if stale is not None:
            raise CertificationError("registration refused: %s" % stale)
        if fact_id in self.state():
            raise CertificationError("fact %s is already registered" % fact_id)
        # A fact enters the trail as candidate regardless of any status a
        # fixture claims: the committed claim is data, never a transition.
        return self._append_event({
            "event_type": "register",
            "fact_id": fact_id,
            "contract_id": contract_id,
            "fact_type": fact.get("fact_type"),
            "evidence_mode": fact.get("evidence_mode"),
            "from_status": None,
            "to_status": "candidate",
            "actor": actor,
            "timestamp": timestamp,
            "reason": "registered from typed-claim contract input",
            "evidence_bundle_ref": None,
            "fact": copy.deepcopy(fact),
        })

    def transition(self, fact_id: str, to_status: str, *, actor: str, timestamp: str,
                   reason: str,
                   two_vote_bundle: Optional[Tuple[os.PathLike[str] | str, str]] = None,
                   packet_dir: os.PathLike[str] | str | None = None,
                   event_type: str = "transition",
                   triggered_by: Optional[str] = None) -> Dict[str, Any]:
        state = self.state()
        entry = state.get(fact_id)
        if entry is None:
            raise CertificationError("unknown fact_id: %s" % fact_id)
        from_status = entry["status"]
        if to_status not in CERT_TRANSITIONS.get(from_status, set()):
            raise CertificationError(
                "illegal certification transition: %s -> %s" % (from_status, to_status)
            )
        evidence_bundle_ref: Optional[Dict[str, Any]] = None
        if to_status == "certified":
            # Producer gate first: a never_auto_resolve producer can never reach
            # certified, however complete its evidence, dependencies or votes.
            refusal = gate_refusal(entry["fact"], contract_id=entry.get("contract_id"))
            if refusal is None:
                refusal = identity_refusal(entry["fact"])
            if refusal is not None:
                raise CertificationError("certification refused for %s: %s" % (fact_id, refusal))
            resolved_tier, _projector_id, _basis = producing_projector_gate(entry["fact"])
            two_vote_row = None
            errors: List[str] = []
            if two_vote_bundle is not None:
                bundle_path, artifact_id = two_vote_bundle
                two_vote_row, bundle_errors = load_two_vote_row(bundle_path, artifact_id)
                errors.extend(bundle_errors)
                if two_vote_row is not None:
                    try:
                        relative = str(Path(bundle_path).resolve().relative_to(ROOT))
                    except ValueError:
                        relative = str(bundle_path)
                    evidence_bundle_ref = {
                        "two_vote_artifact_id": artifact_id,
                        "two_vote_bundle": relative.replace(os.sep, "/"),
                    }
            status_by_id = {key: value["status"] for key, value in state.items()}
            errors.extend(
                evidence_bundle_errors(
                    entry["fact"], status_by_id,
                    two_vote_row=two_vote_row, packet_dir=packet_dir,
                )
            )
            if resolved_tier == "two_vote_required" and two_vote_row is None:
                # The registry gate is authoritative even when the fact type is
                # outside the legacy hard-coded two-vote set.
                errors.append(
                    "the producing projector is gated two_vote_required; a canonical "
                    "two-vote bundle is required"
                )
            if errors:
                raise CertificationError(
                    "certification refused for %s: %s" % (fact_id, "; ".join(errors))
                )
            bundle_summary = {
                "evidence_mode": entry["fact"].get("evidence_mode"),
                "source_addresses": [
                    item.get("address") for item in _addresses(entry["fact"])
                ],
                "dependency_fact_ids": (entry["fact"].get("dependencies") or {}).get("fact_ids", []),
            }
            evidence_bundle_ref = {**bundle_summary, **(evidence_bundle_ref or {})}
        return self._append_event({
            "event_type": event_type,
            "fact_id": fact_id,
            "contract_id": entry.get("contract_id"),
            "fact_type": (entry.get("fact") or {}).get("fact_type"),
            "evidence_mode": (entry.get("fact") or {}).get("evidence_mode"),
            "from_status": from_status,
            "to_status": to_status,
            "actor": actor,
            "timestamp": timestamp,
            "reason": reason,
            "evidence_bundle_ref": evidence_bundle_ref,
            "triggered_by": triggered_by,
        })

    # -- revocation cascade (doc section 5) --------------------------------
    def _dependents_of(self, fact_id: str, state: Dict[str, Dict[str, Any]]) -> List[str]:
        revoked_fact = (state.get(fact_id) or {}).get("fact") or {}
        dependents: List[str] = []
        for dependent_id in revoked_fact.get("dependent_fact_ids") or []:
            if dependent_id in state and dependent_id not in dependents:
                dependents.append(dependent_id)
        for other_id, entry in state.items():
            if other_id == fact_id or other_id in dependents:
                continue
            fact = entry.get("fact") or {}
            depends = set(_derivation_input_ids(fact))
            depends.update((fact.get("dependencies") or {}).get("fact_ids") or [])
            if fact_id in depends:
                dependents.append(other_id)
        return dependents

    def revoke(self, fact_id: str, *, actor: str, timestamp: str,
               reason: str) -> List[Dict[str, Any]]:
        """Revoke a certified fact and mechanically flag every dependent.

        Returns the ordered list of appended events. Deterministic/paired
        derivations from the revoked input are automatically de-certified;
        every other dependent still holding candidate/certified status is
        flagged to review_required. Flagging is mandatory and mechanical;
        re-certification is not (doc section 5.1-5.2).
        """

        state = self.state()
        entry = state.get(fact_id)
        if entry is None:
            raise CertificationError("unknown fact_id: %s" % fact_id)
        if entry["status"] != "certified":
            raise CertificationError(
                "only a certified fact can be revoked (found %s)" % entry["status"]
            )
        events = [self.transition(
            fact_id, "review_required", actor=actor, timestamp=timestamp,
            reason=reason, event_type="revoke",
        )]
        revoke_event_id = events[0]["event_id"]
        visited = {fact_id}
        frontier = [fact_id]
        while frontier:
            current = frontier.pop(0)
            for dependent_id in self._dependents_of(current, state):
                if dependent_id in visited:
                    continue
                visited.add(dependent_id)
                dependent = state[dependent_id]
                status = self.status_by_id().get(dependent_id)
                if status in {"blocked", "rejected", "review_required"}:
                    continue
                mode = (dependent.get("fact") or {}).get("evidence_mode")
                auto = status == "certified" and mode in DERIVED_EVIDENCE_MODES
                events.append(self.transition(
                    dependent_id, "review_required", actor=actor, timestamp=timestamp,
                    reason=(
                        "auto-de-certified: derivation input %s lost certification" % current
                        if auto else
                        "flagged by revocation of %s" % current
                    ),
                    event_type="revoke_cascade",
                    triggered_by=revoke_event_id,
                ))
                lost_certification = status == "certified"
                if lost_certification:
                    frontier.append(dependent_id)
        return events

    # -- validation --------------------------------------------------------
    def validate_trail(self) -> List[str]:
        errors: List[str] = []
        state: Dict[str, Dict[str, Any]] = {}
        previous_line: Optional[str] = None
        for number, event in enumerate(self._events(), 1):
            prefix = "event %d" % number
            if event.get("schema") != EVENT_SCHEMA:
                errors.append("%s: schema must be %s" % (prefix, EVENT_SCHEMA))
            if event.get("seq") != number:
                errors.append(
                    "%s: sequence gap (seq=%r, expected %d) — the trail is append-only"
                    % (prefix, event.get("seq"), number)
                )
            expected_prev = _sha256(previous_line) if previous_line is not None else GENESIS
            if event.get("prev_event_sha256") != expected_prev:
                errors.append("%s: hash chain broken — trail was edited or a line is missing" % prefix)
            for field in ("actor", "timestamp", "fact_id", "event_type"):
                if not event.get(field):
                    errors.append("%s: missing %s" % (prefix, field))
            fact_id = event.get("fact_id")
            if event.get("event_type") == "register":
                if fact_id in state:
                    errors.append("%s: duplicate register for %s" % (prefix, fact_id))
                if event.get("to_status") != "candidate" or event.get("from_status") is not None:
                    errors.append("%s: register must enter as candidate" % prefix)
                if not isinstance(event.get("fact"), dict):
                    errors.append("%s: register must carry the fact payload" % prefix)
                state[fact_id] = {
                    "status": "candidate",
                    "fact": event.get("fact") or {},
                }
            else:
                entry = state.get(fact_id)
                if entry is None:
                    errors.append("%s: transition for unregistered fact %s" % (prefix, fact_id))
                else:
                    if event.get("from_status") != entry["status"]:
                        errors.append(
                            "%s: from_status %r does not match folded state %r"
                            % (prefix, event.get("from_status"), entry["status"])
                        )
                    if event.get("to_status") not in CERT_TRANSITIONS.get(entry["status"], set()):
                        errors.append(
                            "%s: illegal transition %s -> %s"
                            % (prefix, entry["status"], event.get("to_status"))
                        )
                    entry["status"] = event.get("to_status")
                if event.get("to_status") == "certified" and not isinstance(
                    event.get("evidence_bundle_ref"), dict
                ):
                    errors.append("%s: certification event requires an evidence bundle reference" % prefix)
            previous_line = _canonical(event)
        # Cascade invariant: a derived fact may not remain certified after any
        # input fact lost certification (a revoke without cascade is invalid).
        for fact_id, entry in state.items():
            if entry["status"] != "certified":
                continue
            fact = entry.get("fact") or {}
            if fact.get("evidence_mode") not in DERIVED_EVIDENCE_MODES:
                continue
            for input_id in _derivation_input_ids(fact):
                input_state = (state.get(input_id) or {}).get("status")
                if input_state is not None and input_state != "certified":
                    errors.append(
                        "cascade violation: derived fact %s remains certified while "
                        "input %s is %s" % (fact_id, input_id, input_state)
                    )
        return errors


def count_certified(directory: os.PathLike[str] | str | None = None) -> int:
    """Count currently certified typed facts in the event trail store.

    An absent store means zero certified facts — this is the ledger-derived
    tally consumed by build_vn_readiness_v2 / validate_vn_readiness_v2.
    """

    store_dir = Path(directory) if directory is not None else DEFAULT_STORE_DIR
    if not (store_dir / EVENTS_NAME).exists():
        return 0
    store = TypedFactCertificationStore(store_dir)
    errors = store.validate_trail()
    if errors:
        raise CertificationError(
            "certification event trail is invalid: " + "; ".join(errors[:5])
        )
    return len(store.certified_fact_ids())


# ---------------------------------------------------------------------------
# Fixtures and self-test (red-first; discriminators are non-constant)
# ---------------------------------------------------------------------------

_TS = "2026-07-29T00:00:00Z"
_ACTOR = "lane:certify-typed-fact-self-test"

# The fact type these fixtures are stamped with: one whose producer contract is
# REGISTERED (``sarf.documented_form.v1`` -> ``sarf_form``, gate ``auto_safe``), so
# the state machine can be exercised without borrowing anyone's authority.
_FIXTURE_FACT_TYPE = "sarf_form"


def _synthetic_fact(suffix: str, fact_type: str, mode: str, *,
                    addresses: Optional[List[Dict[str, str]]] = None,
                    dependency_ids: Optional[List[str]] = None,
                    chain_inputs: Optional[List[str]] = None,
                    quotation: str = "verbatim source statement") -> Dict[str, Any]:
    """A synthetic fixture for the transition machinery.

    A fixture may never impersonate a recognised typed-claim family: that family's
    authority is a committed contract, an evidence artifact and a declared identity,
    none of which a synthetic fact has. A requested family name is therefore
    recorded as ``fixture_requested_fact_type`` and the fixture is stamped with the
    registered fixture type instead — callers exercising the state machine keep
    working, and no fixture is ever certified under a family it does not belong to.
    Two-vote families are left alone: their authority is a validated vote artifact,
    which a fixture bundle can legitimately supply.
    """

    requested = fact_type
    if fact_type in RECOGNISED_TYPED_CLAIM_FACT_TYPES and fact_type not in TWO_VOTE_FACT_TYPES:
        fact_type = _FIXTURE_FACT_TYPE
    addresses = addresses or [{"address": "quran:2:13:%s" % suffix, "source_kind": "quran_token"}]
    fact: Dict[str, Any] = {
        "fact_id": "sha256:" + hashlib.sha256(("fixture:" + fact_type + ":" + suffix).encode("utf-8")).hexdigest(),
        "fact_type": fact_type,
        "fact_value": {
            "value": "fixture-%s-%s" % (fact_type, suffix),
            "fixture_requested_fact_type": requested,
        },
        "evidence_mode": mode,
        "source_evidence": {
            "source_addresses": copy.deepcopy(addresses),
            "source_quotation": quotation + " [" + suffix + "]",
        },
        "source_address": copy.deepcopy(addresses[0]),
        "dependencies": {
            "fact_ids": list(dependency_ids or []),
            "source_addresses": copy.deepcopy(addresses),
        },
        "derivation_chain": [],
        "contradiction_records": [],
        "defeaters": [],
        "dependent_fact_ids": [],
        "dependent_projection_ids": ["fixture.projection.%s" % suffix],
        "evidence": {"evidence_ids": ["fixture:evidence:%s" % suffix]},
        "certification": {"status": "candidate", "reason": "fixture input"},
        "unresolved_blockers": [],
    }
    if chain_inputs:
        fact["derivation_chain"] = [{
            "step_id": "fixture.step.%s" % suffix,
            "operation": "combine certified inputs",
            "input_fact_ids": list(chain_inputs),
            "output": "derived fixture value %s" % suffix,
        }]
    return fact


def _expect_refusal(label: str, needle: str, callable_, *args: Any, **kwargs: Any) -> bool:
    try:
        callable_(*args, **kwargs)
    except CertificationError as exc:
        if needle in str(exc):
            return True
        print("SELF-TEST FAIL %s: expected refusal containing %r, got: %s" % (label, needle, exc))
        return False
    print("SELF-TEST FAIL %s: transition was accepted but must be refused" % label)
    return False


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="certify-typed-fact-") as td:
        store = TypedFactCertificationStore(os.path.join(td, "store"))

        attested = _synthetic_fact("21", _FIXTURE_FACT_TYPE, "direct_source_attestation")
        corroborated = _synthetic_fact(
            "22", _FIXTURE_FACT_TYPE, "cross_source_corroboration",
            addresses=[
                {"address": "quran:2:13:22", "source_kind": "quran_token"},
                {"address": "entry:fixture22:root", "source_kind": "qamus_entry_field"},
            ],
        )
        derived = _synthetic_fact(
            "23", _FIXTURE_FACT_TYPE, "deterministic_derivation_from_certified_facts",
            dependency_ids=[attested["fact_id"], corroborated["fact_id"]],
            chain_inputs=[attested["fact_id"], corroborated["fact_id"]],
        )
        for fact in (attested, corroborated, derived):
            store.register(fact, contract_id="fixture:contract", actor=_ACTOR, timestamp=_TS)

        # Red 1: candidate -> certified must not skip review.
        if not _expect_refusal(
            "skip-review", "illegal certification transition",
            store.transition, attested["fact_id"], "certified",
            actor=_ACTOR, timestamp=_TS, reason="skip",
        ):
            return 1

        store.transition(attested["fact_id"], "review_required", actor=_ACTOR,
                         timestamp=_TS, reason="bundle assembled")

        # Red 2: deterministic derivation over candidate inputs (FAM4/FAM5 closure).
        store.transition(derived["fact_id"], "review_required", actor=_ACTOR,
                         timestamp=_TS, reason="bundle assembled")
        if not _expect_refusal(
            "deterministic-over-candidate", "requires every input fact to be certified",
            store.transition, derived["fact_id"], "certified",
            actor=_ACTOR, timestamp=_TS, reason="premature",
        ):
            return 1

        # Red 3: certification without an evidence bundle.
        naked = _synthetic_fact("24", _FIXTURE_FACT_TYPE, "direct_source_attestation")
        del naked["source_evidence"]
        store.register(naked, contract_id="fixture:contract", actor=_ACTOR, timestamp=_TS)
        store.transition(naked["fact_id"], "review_required", actor=_ACTOR,
                         timestamp=_TS, reason="bundle assembled")
        if not _expect_refusal(
            "certify-without-bundle", "requires a source_evidence bundle",
            store.transition, naked["fact_id"], "certified",
            actor=_ACTOR, timestamp=_TS, reason="no bundle",
        ):
            return 1

        # Red 4: same-family repetition is not corroboration.
        repeated = _synthetic_fact(
            "25", _FIXTURE_FACT_TYPE, "cross_source_corroboration",
            addresses=[
                {"address": "quran:2:13:25", "source_kind": "quran_token"},
                {"address": "quran:2:282:25", "source_kind": "quran_token"},
            ],
        )
        store.register(repeated, contract_id="fixture:contract", actor=_ACTOR, timestamp=_TS)
        store.transition(repeated["fact_id"], "review_required", actor=_ACTOR,
                         timestamp=_TS, reason="bundle assembled")
        if not _expect_refusal(
            "same-family-corroboration", "distinct source families",
            store.transition, repeated["fact_id"], "certified",
            actor=_ACTOR, timestamp=_TS, reason="repetition",
        ):
            return 1

        # Red 5: two-vote rung without an artifact bundle.
        governed = _synthetic_fact(
            "12", "governor_relation", "direct_source_attestation",
            addresses=[{"address": "quran:2:13:12", "source_kind": "quran_token"}],
        )
        store.register(governed, contract_id="fixture:contract", actor=_ACTOR, timestamp=_TS)
        store.transition(governed["fact_id"], "review_required", actor=_ACTOR,
                         timestamp=_TS, reason="bundle assembled")
        if not _expect_refusal(
            "two-vote-missing", "two-vote", store.transition,
            governed["fact_id"], "certified", actor=_ACTOR, timestamp=_TS, reason="no artifact",
        ):
            return 1

        # Red 6: a failing bundle is refused because the validator is CONSUMED,
        # never re-derived — a same-engine pair fails validate_two_vote_artifacts.
        bad_bundle = os.path.join(td, "bad-two-vote.jsonl")
        broken = two_vote.sample_verified_row()
        broken["votes"][1]["reviewer"]["engine"] = broken["votes"][0]["reviewer"]["engine"]
        two_vote.write_jsonl(bad_bundle, [broken])
        if not _expect_refusal(
            "two-vote-nonindependent", "fails validate_two_vote_artifacts",
            store.transition, governed["fact_id"], "certified",
            actor=_ACTOR, timestamp=_TS, reason="bad bundle",
            two_vote_bundle=(bad_bundle, broken["artifact_id"]),
        ):
            return 1

        # Green: attestation, corroboration, two-vote and derived certifications.
        good_bundle = os.path.join(td, "good-two-vote.jsonl")
        two_vote.write_jsonl(good_bundle, [two_vote.sample_verified_row()])
        store.transition(attested["fact_id"], "certified", actor=_ACTOR, timestamp=_TS,
                         reason="direct attestation bundle complete")
        store.transition(corroborated["fact_id"], "review_required", actor=_ACTOR,
                         timestamp=_TS, reason="bundle assembled")
        store.transition(corroborated["fact_id"], "certified", actor=_ACTOR, timestamp=_TS,
                         reason="two independent source families agree")
        store.transition(derived["fact_id"], "certified", actor=_ACTOR, timestamp=_TS,
                         reason="all derivation inputs are certified")
        store.transition(governed["fact_id"], "certified", actor=_ACTOR, timestamp=_TS,
                         reason="verified two-vote artifact consumed",
                         two_vote_bundle=(good_bundle, "two-vote-artifact:quran_2_13_12"))
        if store.certified_fact_ids() != sorted([
            attested["fact_id"], corroborated["fact_id"], derived["fact_id"], governed["fact_id"],
        ]):
            print("SELF-TEST FAIL: certified set mismatch after green transitions")
            return 1
        if count_certified(store.directory) != 4:
            print("SELF-TEST FAIL: count_certified does not match the trail")
            return 1
        if count_certified(os.path.join(td, "absent-store")) != 0:
            print("SELF-TEST FAIL: an absent store must count zero certified facts")
            return 1

        # Green + red 7: revocation cascade — revoking a root drops the
        # dependent derived fact automatically.
        events = store.revoke(attested["fact_id"], actor=_ACTOR, timestamp=_TS,
                              reason="source capture corrected")
        statuses = store.status_by_id()
        if statuses[attested["fact_id"]] != "review_required":
            print("SELF-TEST FAIL: revoked fact did not drop to review_required")
            return 1
        if statuses[derived["fact_id"]] != "review_required":
            print("SELF-TEST FAIL: derived dependent was not auto-de-certified on revocation")
            return 1
        if not any(event.get("event_type") == "revoke_cascade" for event in events):
            print("SELF-TEST FAIL: revocation produced no cascade events")
            return 1
        if statuses[corroborated["fact_id"]] != "certified":
            print("SELF-TEST FAIL: unrelated certified fact must be untouched by the cascade")
            return 1
        if store.validate_trail():
            print("SELF-TEST FAIL: valid trail reported errors:", store.validate_trail()[:3])
            return 1

        # Red 8: a revoke WITHOUT cascade is detectable — forge a bare drop of
        # the corroborated input under a certified derived fact.
        forged_dir = os.path.join(td, "forged")
        forged = TypedFactCertificationStore(forged_dir)
        base_input = _synthetic_fact("31", _FIXTURE_FACT_TYPE, "direct_source_attestation")
        base_derived = _synthetic_fact(
            "32", _FIXTURE_FACT_TYPE, "paired_form_inference",
            dependency_ids=[base_input["fact_id"]],
            chain_inputs=[base_input["fact_id"]],
        )
        forged.register(base_input, contract_id="fixture:contract", actor=_ACTOR, timestamp=_TS)
        forged.register(base_derived, contract_id="fixture:contract", actor=_ACTOR, timestamp=_TS)
        forged.transition(base_input["fact_id"], "review_required", actor=_ACTOR,
                          timestamp=_TS, reason="bundle assembled")
        forged.transition(base_input["fact_id"], "certified", actor=_ACTOR,
                          timestamp=_TS, reason="attested")
        forged.transition(base_derived["fact_id"], "review_required", actor=_ACTOR,
                          timestamp=_TS, reason="bundle assembled")
        forged.transition(base_derived["fact_id"], "certified", actor=_ACTOR,
                          timestamp=_TS, reason="derived from certified input")
        # Bypass revoke(): append a bare drop event with no cascade.
        forged._append_event({
            "event_type": "revoke",
            "fact_id": base_input["fact_id"],
            "contract_id": "fixture:contract",
            "fact_type": base_input["fact_type"],
            "evidence_mode": base_input["evidence_mode"],
            "from_status": "certified",
            "to_status": "review_required",
            "actor": _ACTOR,
            "timestamp": _TS,
            "reason": "forged revoke without cascade",
            "evidence_bundle_ref": None,
            "triggered_by": None,
        })
        forged_errors = forged.validate_trail()
        if not any("cascade violation" in err for err in forged_errors):
            print("SELF-TEST FAIL: revoke-without-cascade was not detected:", forged_errors[:3])
            return 1

        # Red 9: an event-trail gap (deleted line) fails closed.
        lines = store.events_path.read_text(encoding="utf-8").splitlines()
        gapped_dir = Path(td) / "gapped"
        gapped_dir.mkdir()
        (gapped_dir / EVENTS_NAME).write_text(
            "\n".join(lines[:3] + lines[4:]) + "\n", encoding="utf-8"
        )
        gap_errors = TypedFactCertificationStore(gapped_dir).validate_trail()
        if not any("sequence gap" in err for err in gap_errors) or not any(
            "hash chain broken" in err for err in gap_errors
        ):
            print("SELF-TEST FAIL: event trail gap was not detected:", gap_errors[:3])
            return 1

        # Red 10: in-place edit of an event breaks the hash chain.
        edited_dir = Path(td) / "edited"
        edited_dir.mkdir()
        edited_lines = list(lines)
        edited_lines[2] = edited_lines[2].replace(_ACTOR, "lane:someone-else")
        (edited_dir / EVENTS_NAME).write_text("\n".join(edited_lines) + "\n", encoding="utf-8")
        edit_errors = TypedFactCertificationStore(edited_dir).validate_trail()
        if not any("hash chain broken" in err for err in edit_errors):
            print("SELF-TEST FAIL: in-place event edit was not detected:", edit_errors[:3])
            return 1

    print("CERTIFY TYPED FACT SELF-TEST PASS")
    return 0


# ---------------------------------------------------------------------------
# Worked example: the sufaha canary contract (read-only over committed files)
# ---------------------------------------------------------------------------

def _sufaha_dependency_order(facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ordered: List[Dict[str, Any]] = []
    pending = list(facts)
    placed: set = set()
    while pending:
        progressed = False
        for fact in list(pending):
            inputs = set(_derivation_input_ids(fact))
            if inputs <= placed:
                ordered.append(fact)
                placed.add(fact["fact_id"])
                pending.remove(fact)
                progressed = True
        if not progressed:
            raise CertificationError("cyclic derivation dependencies in contract facts")
    return ordered


def demo_sufaha() -> int:
    contract = json.loads(SUFAHA_CONTRACT.read_text(encoding="utf-8"))
    facts = contract.get("facts", [])
    contract_id = contract.get("contract_id", "fd:sufaha:2:13:12")
    packet_dir = SUFAHA_CONTRACT.parent
    actor = "lane:certify-typed-fact-sufaha-demo"
    print("SUFAHA demo: %d owner-recorded facts loaded from %s (read-only)"
          % (len(facts), SUFAHA_CONTRACT.relative_to(ROOT)))

    with tempfile.TemporaryDirectory(prefix="certify-sufaha-") as td:
        # Leg A — the committed packet, honestly refused: the review-artifact
        # evidence file the facts address (sufaha-evidence.jsonl, the MCP
        # verbatim capture) is not committed in-repo, so no fact may be
        # hard-certified and the committed contract stays untouched.
        store_a = TypedFactCertificationStore(os.path.join(td, "committed"))
        refused = 0
        blockers: set = set()
        for fact in facts:
            store_a.register(fact, contract_id=contract_id, actor=actor, timestamp=_TS)
            store_a.transition(fact["fact_id"], "review_required", actor=actor,
                               timestamp=_TS, reason="owner-recorded bundle under review")
        for fact in _sufaha_dependency_order(facts):
            kwargs: Dict[str, Any] = {"packet_dir": packet_dir}
            if fact.get("fact_type") in TWO_VOTE_FACT_TYPES:
                kwargs["two_vote_bundle"] = (TWO_VOTE_SAMPLE, "two-vote-artifact:quran_2_13_12")
            try:
                store_a.transition(fact["fact_id"], "certified", actor=actor,
                                   timestamp=_TS, reason="attempt against committed packet",
                                   **kwargs)
            except CertificationError as exc:
                refused += 1
                if "not committed in-repo" in str(exc):
                    blockers.add("sufaha-evidence.jsonl not committed in-repo")
        if refused != len(facts) or blockers != {"sufaha-evidence.jsonl not committed in-repo"}:
            print("SUFAHA DEMO FAIL: committed packet leg expected %d honest refusals "
                  "on the missing in-repo evidence file, saw %d (%s)"
                  % (len(facts), refused, sorted(blockers)))
            return 1
        if store_a.certified_fact_ids():
            print("SUFAHA DEMO FAIL: no committed-packet fact may reach certified")
            return 1
        print("  leg A (committed packet): 0/%d certified — every certification "
              "honestly refused; blocker: the facts' review-artifact address "
              "(sufaha-evidence.jsonl, MCP verbatim capture) is not committed in-repo"
              % len(facts))

        # Leg B — a resolvable fixture packet does NOT confer family authority.
        # The temp packet dir carries a clearly-marked stand-in evidence file built
        # ONLY from quotations already committed inside sufaha-contract.json. It
        # makes the review-artifact address resolvable, and it still changes
        # nothing: the ten non-two-vote families draw their authority from the
        # committed family contract, whose declared evidence file is absent from
        # this repository, so they stay refused. Only governor_relation may certify,
        # because a validated two-vote artifact is its authority.
        fixture_packet = Path(td) / "fixture-packet"
        fixture_packet.mkdir()
        standin_rows = [
            {
                "fixture_standin": True,
                "source": "qamus/examples/proof-noun-sufaha/sufaha-contract.json",
                "fact_index": index + 1,
                "fact_type": fact.get("fact_type"),
                "source_quotation": (fact.get("source_evidence") or {}).get("source_quotation"),
            }
            for index, fact in enumerate(facts)
        ]
        with (fixture_packet / "sufaha-evidence.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            for row in standin_rows:
                handle.write(_canonical(row) + "\n")

        store_b = TypedFactCertificationStore(os.path.join(td, "fixture"))
        for fact in facts:
            store_b.register(fact, contract_id=contract_id, actor=actor, timestamp=_TS)
            store_b.transition(fact["fact_id"], "review_required", actor=actor,
                               timestamp=_TS, reason="fixture bundle under review")
        certified_types: List[str] = []
        family_refusals: Dict[str, str] = {}
        for fact in _sufaha_dependency_order(facts):
            kwargs = {"packet_dir": fixture_packet}
            if fact.get("fact_type") in TWO_VOTE_FACT_TYPES:
                kwargs["two_vote_bundle"] = (TWO_VOTE_SAMPLE, "two-vote-artifact:quran_2_13_12")
            try:
                store_b.transition(fact["fact_id"], "certified", actor=actor, timestamp=_TS,
                                   reason="fixture packet bundle (%s)" % fact.get("evidence_mode"),
                                   **kwargs)
                certified_types.append(str(fact.get("fact_type")))
            except CertificationError as exc:
                family_refusals[str(fact.get("fact_type"))] = str(exc)
        expected = sorted(str(fact.get("fact_type")) for fact in facts
                          if fact.get("fact_type") in TWO_VOTE_FACT_TYPES)
        if sorted(certified_types) != expected:
            print("SUFAHA DEMO FAIL: fixture packet certified %s, expected exactly the "
                  "two-vote families %s" % (sorted(certified_types), expected))
            return 1
        if not family_refusals or not all(
                "not committed in-repo" in message for message in family_refusals.values()):
            print("SUFAHA DEMO FAIL: family refusals must all name the uncommitted evidence:",
                  sorted(family_refusals)[:3])
            return 1
        print("  leg B (resolvable fixture packet): %d/%d certified — only %s, whose authority is "
              "the CONSUMED two-vote artifact (%s); the %d family facts stay refused even with the "
              "cited artifact present in the packet, because %s declares that evidence in-repo and "
              "it is not committed"
              % (len(certified_types), len(facts), ", ".join(expected),
                 TWO_VOTE_SAMPLE.relative_to(ROOT), len(family_refusals),
                 SUFAHA_CONTRACT.relative_to(ROOT).as_posix()))

        # Leg C — revocation over the one fact that could certify. No cascade is
        # possible here and none is claimed: nothing in this packet derives from the
        # two-vote fact, and the derivations that DO exist could never certify. The
        # cascade itself is exercised in --self-test, over a fact type with a
        # registered producer contract, so no family name has to be borrowed.
        certified_ids = store_b.certified_fact_ids()
        events = store_b.revoke(certified_ids[0], actor=actor, timestamp=_TS,
                                reason="demo: two-vote artifact withdrawn")
        statuses = store_b.status_by_id()
        cascade = [event for event in events if event["event_type"] == "revoke_cascade"]
        if statuses[certified_ids[0]] != "review_required":
            print("SUFAHA DEMO FAIL: revoked fact did not drop to review_required")
            return 1
        if cascade:
            print("SUFAHA DEMO FAIL: a cascade was reported where no dependent was certified")
            return 1
        if store_b.certified_fact_ids():
            print("SUFAHA DEMO FAIL: a certified fact survived its own revocation")
            return 1
        trail_errors = store_b.validate_trail()
        if trail_errors:
            print("SUFAHA DEMO FAIL: fixture trail invalid:", trail_errors[:3])
            return 1
        print("  leg C (revocation): revoking the one certified fact left 0 certified and 0 "
              "cascade events — honestly, because no certified dependent exists to drop; the "
              "cascade machinery is exercised by --self-test, and the trail validates")

    print("  committed artifacts untouched: certification was demonstrated only in "
          "temp stores; the in-repo blocker (uncommitted MCP verbatim evidence) is "
          "recorded above")
    print("SUFAHA CERTIFIER DEMO PASS")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true",
                        help="run the red-first offline self-test")
    parser.add_argument("--demo-sufaha", action="store_true",
                        help="run the sufaha canary worked example (read-only)")
    parser.add_argument("--count", metavar="DIR", nargs="?", const=str(DEFAULT_STORE_DIR),
                        help="print the certified-fact count for a store directory")
    parser.add_argument("--validate", metavar="DIR",
                        help="validate an event trail store directory")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            return self_test()
        if args.demo_sufaha:
            return demo_sufaha()
        if args.validate:
            errors = TypedFactCertificationStore(args.validate).validate_trail()
            if errors:
                for error in errors:
                    print("ERROR " + error, file=sys.stderr)
                return 1
            print("OK: certification event trail is valid")
            return 0
        if args.count is not None:
            print(count_certified(args.count))
            return 0
        parser.error("one of --self-test, --demo-sufaha, --count, --validate is required")
    except CertificationError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
