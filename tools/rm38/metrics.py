from __future__ import annotations

import math
import bisect
import unicodedata
from collections import Counter, defaultdict
from typing import Any

from tools.normalize_ar import norm_strict
from tools.rm38.crosswalks import coarse_pos, relation_label, segment_boundaries


BUCKETS = (
    "segmentation_mismatch", "pos_mismatch", "feature_mismatch", "lemma_mismatch",
    "root_mismatch", "governor_mismatch", "abstention", "gold_error_candidate",
    "tokenization_boundary_artifact", "needs_manual_triage",
)


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": round(numerator / denominator, 6) if denominator else None,
    }


def _candidate_value(candidate: dict[str, Any], layer: str, source: str) -> Any:
    if layer == "pos":
        return coarse_pos(candidate.get("pos"), source=source)
    if layer in ("lemma", "root"):
        value = candidate.get(layer)
        return norm_strict(str(value)) if value else None
    return candidate.get(layer)


def _gold_value(gold: dict[str, Any], layer: str, source: str) -> Any:
    if layer == "pos":
        return coarse_pos(gold.get("pos"), source=source)
    if layer in ("lemma", "root"):
        value = gold.get(layer)
        return norm_strict(str(value)) if value else None
    return gold.get(layer)


def _mark_present(text: str) -> bool:
    return any(unicodedata.category(ch) == "Mn" for ch in text)


def derive_score_bin_edges(rows: list[dict[str, Any]]) -> list[float]:
    scores = sorted(
        float(candidates[0]["score"])
        for row in rows
        for candidates in [(row.get("engine") or {}).get("candidates") or []]
        if candidates and isinstance(candidates[0].get("score"), (int, float))
    )
    if not scores:
        return []
    edges = []
    for quantile in range(1, 10):
        index = min(len(scores) - 1, math.ceil(len(scores) * quantile / 10) - 1)
        edge = scores[index]
        if not edges or edge > edges[-1]:
            edges.append(edge)
    return edges


def _calibration(outcomes: list[tuple[dict[str, Any], bool]], score_bin_edges: list[float],
                 score_edge_source: str) -> dict[str, Any]:
    confidence_bins: dict[str, list[bool]] = defaultdict(list)
    score_bins: dict[int, list[bool]] = defaultdict(list)
    for candidate, correct in outcomes:
        confidence_bins[str(candidate.get("confidence") or "unknown")].append(correct)
        score = candidate.get("score")
        if isinstance(score, (int, float)):
            score_bins[bisect.bisect_right(score_bin_edges, float(score))].append(correct)
    bins = []
    ece_numerator = 0.0
    total = len(outcomes)
    expected = {"high": 0.9, "medium": 0.6, "low": 0.3, "unknown": 0.5}
    for label in sorted(confidence_bins):
        values = confidence_bins[label]
        accuracy = sum(values) / len(values)
        ece_numerator += len(values) * abs(accuracy - expected.get(label, 0.5))
        bins.append({"kind": "confidence", "bin": label, "n": len(values), "accuracy": round(accuracy, 6)})
    for decile in sorted(score_bins):
        values = score_bins[decile]
        bins.append({"kind": "score_decile", "bin": decile, "n": len(values),
                     "accuracy": round(sum(values) / len(values), 6)})
    return {
        "bins": bins,
        "ece": round(ece_numerator / total, 6) if total else None,
        "score_bin_edges": score_bin_edges,
        "score_edge_source": score_edge_source,
    }


def _gold_sources_disagree(row: dict[str, Any], layer: str) -> bool:
    left = row.get("quranmorph") or {}
    right = row.get("eqtb") or {}
    if not left or not right:
        return False
    if layer == "features":
        common = set(left.get("features") or {}) & set(right.get("features") or {})
        return any(left["features"].get(key) != right["features"].get(key) for key in common)
    if layer == "governor":
        return False
    return _gold_value(left, layer, "quranmorph") != _gold_value(right, layer, "eqtb")


def _segments_match(row: dict[str, Any], gold: dict[str, Any]) -> bool:
    surface = str(row.get("surface") or gold.get("surface") or "")
    engine_segments = (row.get("engine") or {}).get("segments") or [surface]
    gold_segments = gold.get("segments") or [gold.get("surface") or surface]
    return segment_boundaries(engine_segments, surface) == segment_boundaries(gold_segments, surface)


def evaluate_layer(rows: list[dict[str, Any]], *, source: str, layer: str, split: str,
                   citation: str = "synthetic self-test", license_name: str = "CC BY 4.0",
                   score_bin_edges: list[float] | None = None, score_edge_source: str | None = None) -> dict[str, Any]:
    if source not in {"quranmorph", "eqtb"}:
        raise ValueError(f"unsupported source: {source}")
    if layer not in {"segmentation", "pos", "lemma", "root", "features", "governor"}:
        raise ValueError(f"unsupported layer: {layer}")
    if score_bin_edges is None:
        score_bin_edges = derive_score_bin_edges(rows)
    if score_edge_source is None:
        score_edge_source = split
    buckets = Counter({name: 0 for name in BUCKETS})
    flags: set[str] = set()
    if source == "eqtb":
        flags.add("orthography:uthmani")
    n_gold = n_alignable = emitted = correct = wrong_resolved = abstained = 0
    recall1_hits = recallk_hits = recall_denominator = 0
    calibration_rows: list[tuple[dict[str, Any], bool]] = []
    rank_dist = Counter({"rank_1": 0, "lower_rank": 0, "none": 0})
    feature_counts: dict[str, Counter[str]] = defaultdict(Counter)
    provenance: dict[str, Counter[str]] = defaultdict(Counter)
    uas_hits = las_hits = governor_emitted = 0
    abstention_matrix = Counter({
        "emit_gold_agrees_with_top": 0,
        "emit_gold_disagrees_with_top": 0,
        "abstain_gold_agrees_with_top": 0,
        "abstain_gold_disagrees_with_top": 0,
    })
    disagreements: list[dict[str, Any]] = []
    classified_tokens: set[str] = set()
    inter_gold_present = inter_gold_aligned = inter_gold_unalignable = 0
    inter_gold_disagreements = 0

    def classify(row: dict[str, Any], bucket: str, **details: Any) -> None:
        token_id = str(row.get("token_id") or row.get("surface") or f"row:{len(classified_tokens)}")
        if token_id in classified_tokens:
            return
        classified_tokens.add(token_id)
        buckets[bucket] += 1
        item = {"token_id": token_id, "bucket": bucket}
        if details:
            item["details"] = details
        disagreements.append(item)

    for row in rows:
        gold = row.get(source)
        if not isinstance(gold, dict):
            continue
        n_gold += 1
        inter_gold_present += int(bool(row.get("_inter_gold_unit_present")))
        inter_gold_aligned += int(isinstance(row.get("eqtb" if source == "quranmorph" else "quranmorph"), dict))
        inter_gold_unalignable += int(bool(row.get("_inter_gold_unalignable")))
        engine = row.get("engine") or {}
        if norm_strict(str(row.get("surface") or "")) != norm_strict(str(gold.get("surface") or row.get("surface") or "")):
            classify(row, "tokenization_boundary_artifact", reason="norm_strict_surface_span")
            continue
        if not _segments_match(row, gold):
            classify(row, "tokenization_boundary_artifact", reason="segment_boundary")
            continue
        n_alignable += 1
        if layer == "segmentation":
            emitted += 1
            correct += 1
            abstention_matrix["emit_gold_agrees_with_top"] += 1
            continue
        candidates = list(engine.get("candidates") or [])
        top = candidates[0] if candidates else {}
        is_pending = engine.get("status") in {"pending", "abstain", None}
        contested = _gold_sources_disagree(row, layer)
        if contested:
            inter_gold_disagreements += 1
            flags.add("inter-gold-disagreement")
            classify(row, "gold_error_candidate", reason="inter-gold-disagreement")

        if layer == "governor":
            if source != "eqtb":
                flags.add("unevaluable-against-quranmorph")
                continue
            gold_head = gold.get("governor")
            gold_relation = relation_label(gold.get("relation"))
            head = engine.get("governor")
            relation = relation_label(engine.get("relation"))
            prov = str(gold.get("syntax_provenance") or "unspecified")
            recall_denominator += int(gold_head not in (None, ""))
            if head not in (None, "") and gold_head not in (None, "") and str(head) == str(gold_head):
                recall1_hits += 1
                recallk_hits += 1
            if head in (None, "") or is_pending:
                abstained += 1
                abstention_matrix["abstain_gold_disagrees_with_top"] += 1
                classify(row, "abstention", layer="governor")
                provenance[prov]["abstained"] += 1
                continue
            emitted += 1
            governor_emitted += 1
            head_ok = str(head) == str(gold_head)
            label_ok = head_ok and relation is not None and relation == gold_relation
            abstention_matrix["emit_gold_agrees_with_top" if label_ok else "emit_gold_disagrees_with_top"] += 1
            uas_hits += int(head_ok)
            las_hits += int(label_ok)
            provenance[prov]["emitted"] += 1
            provenance[prov]["uas_hits"] += int(head_ok)
            provenance[prov]["las_hits"] += int(label_ok)
            if label_ok:
                correct += 1
            elif not contested:
                wrong_resolved += 1
                classify(row, "governor_mismatch", head_mismatch=not head_ok, relation_mismatch=head_ok and not label_ok)
            continue

        if layer == "features":
            gold_features = gold.get("features") or {}
            engine_features = top.get("features") or {}
            comparable = False
            any_wrong = False
            any_emitted = False
            top_agrees = True
            top_has_value = False
            voweled_surface = _mark_present(str(row.get("surface") or gold.get("surface") or ""))
            for feature, gold_value in sorted(gold_features.items()):
                if gold_value in (None, ""):
                    continue
                comparable = True
                feature_counts[feature]["gold"] += 1
                if feature in {"case", "mood"}:
                    feature_counts[feature]["voweled_gold" if voweled_surface else "unvoweled_gold"] += 1
                value = engine_features.get(feature)
                if value not in (None, ""):
                    top_has_value = True
                if value in (None, "") or str(value) != str(gold_value):
                    top_agrees = False
                if value in (None, "") or is_pending:
                    feature_counts[feature]["abstained"] += 1
                    if feature in {"case", "mood"} and not voweled_surface:
                        feature_counts[feature]["unvoweled_abstained"] += 1
                    continue
                any_emitted = True
                feature_counts[feature]["emitted"] += 1
                if feature in {"case", "mood"} and voweled_surface:
                    feature_counts[feature]["voweled_emitted"] += 1
                if str(value) == str(gold_value):
                    feature_counts[feature]["correct"] += 1
                    if feature in {"case", "mood"} and voweled_surface:
                        feature_counts[feature]["voweled_correct"] += 1
                else:
                    feature_counts[feature]["wrong"] += 1
                    any_wrong = True
            if not comparable:
                continue
            if any_emitted:
                emitted += 1
                abstention_matrix["emit_gold_agrees_with_top" if top_agrees else "emit_gold_disagrees_with_top"] += 1
                if any_wrong:
                    if not contested:
                        wrong_resolved += 1
                    classify(row, "feature_mismatch")
                else:
                    correct += 1
            else:
                abstained += 1
                abstention_matrix[
                    "abstain_gold_agrees_with_top" if top_has_value and top_agrees
                    else "abstain_gold_disagrees_with_top"
                ] += 1
                classify(row, "abstention", layer="features")
            if top_has_value:
                calibration_rows.append((top, top_agrees))
            continue

        gold_value = _gold_value(gold, layer, source)
        if gold_value is None:
            continue
        candidate_values = [_candidate_value(candidate, layer, source) for candidate in candidates]
        recall_denominator += 1
        rank = next((index + 1 for index, value in enumerate(candidate_values) if value == gold_value), None)
        recall1_hits += int(rank == 1)
        recallk_hits += int(rank is not None)
        if len(candidates) > 1:
            rank_dist["rank_1" if rank == 1 else "lower_rank" if rank else "none"] += 1
        top_value = candidate_values[0] if candidate_values else None
        if top_value is not None:
            calibration_rows.append((top, top_value == gold_value))
        if top_value is None or is_pending:
            abstained += 1
            abstention_matrix[
                "abstain_gold_agrees_with_top" if top_value == gold_value
                else "abstain_gold_disagrees_with_top"
            ] += 1
            classify(row, "abstention", layer=layer)
            continue
        emitted += 1
        agrees = top_value == gold_value
        abstention_matrix["emit_gold_agrees_with_top" if agrees else "emit_gold_disagrees_with_top"] += 1
        if agrees:
            correct += 1
        elif not contested:
            wrong_resolved += 1
            bucket = {"pos": "pos_mismatch", "lemma": "lemma_mismatch", "root": "root_mismatch"}[layer]
            classify(row, bucket)

    coverage = _ratio(emitted, n_alignable)
    report: dict[str, Any] = {
        "source": source,
        "layer": layer,
        "split": split,
        "denominator_definition": "gold-covered, norm_strict-span-alignable tokens; boundary artifacts quarantined",
        "n_gold": n_gold,
        "n_alignable": n_alignable,
        "coverage": coverage,
        "abstention_rate": _ratio(abstained, n_alignable),
        "abstention_matrix": dict(sorted(abstention_matrix.items())),
        "wrong_resolve_rate": _ratio(wrong_resolved, n_alignable),
        "emit_accuracy": _ratio(correct, emitted),
        "candidate_recall@1": _ratio(recall1_hits, recall_denominator),
        "candidate_recall@k": _ratio(recallk_hits, recall_denominator),
        "calibration": _calibration(calibration_rows, score_bin_edges, score_edge_source),
        "alternatives_retained": {"rank_dist": dict(sorted(rank_dist.items()))},
        "buckets": dict(sorted(buckets.items())),
        "disagreements": disagreements,
        "flags": sorted(flags),
        "citation": citation,
        "license": license_name,
        "inter_gold_alignment": {
            "n_unit_present": inter_gold_present,
            "n_aligned": inter_gold_aligned,
            "n_quarantined": inter_gold_unalignable,
            "agreement_rate": _ratio(inter_gold_aligned - inter_gold_disagreements, inter_gold_aligned),
        },
    }
    if layer == "features":
        per_feature = {}
        for feature, counts in sorted(feature_counts.items()):
            per_feature[feature] = {
                "coverage": _ratio(counts["emitted"], counts["gold"]),
                "emit_accuracy": _ratio(counts["correct"], counts["emitted"]),
                "abstention_rate": _ratio(counts["abstained"], counts["gold"]),
            }
        case_mood = {}
        for feature in ("case", "mood"):
            counts = feature_counts[feature]
            case_mood[feature] = {
                "voweled_subset_accuracy": _ratio(counts["voweled_correct"], counts["voweled_emitted"]),
                "unvoweled_abstention_rate": _ratio(counts["unvoweled_abstained"], counts["unvoweled_gold"]),
            }
        report["per_feature"] = per_feature
        report["case_mood"] = case_mood
    if layer == "governor" and source == "eqtb":
        report["uas"] = _ratio(uas_hits, governor_emitted)
        report["las"] = _ratio(las_hits, governor_emitted)
        report["eqtb_syntax_is_partly_dl_silver"] = True
        report["provenance_split"] = {
            key: {
                "n_emitted": value["emitted"],
                "n_abstained": value["abstained"],
                "uas": _ratio(value["uas_hits"], value["emitted"]),
                "las": _ratio(value["las_hits"], value["emitted"]),
            }
            for key, value in sorted(provenance.items())
        }
        report["flags"] = sorted(set(report["flags"]) | {"EQTB syntax partly DL-silver"})
    return report
