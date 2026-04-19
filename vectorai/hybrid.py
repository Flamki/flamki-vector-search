from __future__ import annotations


def reciprocal_rank_fusion(ranked_lists: list[list[dict]], k: int = 60) -> list[dict]:
    """
    Merge ranked result lists using Reciprocal Rank Fusion (RRF).

    Each list item is expected to include `path`, and may include any
    additional metadata fields.
    """
    scores: dict[str, dict] = {}

    for ranked in ranked_lists:
        for rank, item in enumerate(ranked):
            path = item.get("path")
            if not path:
                continue

            if path not in scores:
                scores[path] = {"score": 0.0, "item": dict(item)}
            scores[path]["score"] += 1.0 / (k + rank + 1)

    merged = []
    for payload in scores.values():
        out = dict(payload["item"])
        out["rrf_score"] = payload["score"]
        merged.append(out)

    merged.sort(key=lambda x: x["rrf_score"], reverse=True)
    return merged
