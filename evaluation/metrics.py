"""
Evaluation script – precision / recall per detection type.
Run on recorded test videos with ground-truth labels.
Also supports fairness groups (skin tone, glasses, lighting).
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def load_ground_truth(path: str) -> List[dict]:
    with open(path) as f:
        return json.load(f)


def evaluate(predictions: List[dict], ground_truth: List[dict], iou_threshold: float = 0.5) -> Dict:
    """
    Simple event-level evaluation.
    predictions / ground_truth: list of {"type": str, "start_ts": float, "end_ts": float}
    """
    results = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    gt_by_type = defaultdict(list)
    for g in ground_truth:
        gt_by_type[g["type"]].append(g)

    pred_by_type = defaultdict(list)
    for p in predictions:
        pred_by_type[p["type"]].append(p)

    all_types = set(gt_by_type) | set(pred_by_type)

    for t in all_types:
        gts = gt_by_type[t]
        preds = pred_by_type[t]
        matched_gt = set()

        for p in preds:
            matched = False
            for i, g in enumerate(gts):
                if i in matched_gt:
                    continue
                # temporal overlap
                overlap = max(0, min(p["end_ts"], g["end_ts"]) - max(p["start_ts"], g["start_ts"]))
                union = max(p["end_ts"], g["end_ts"]) - min(p["start_ts"], g["start_ts"])
                if union > 0 and overlap / union >= iou_threshold:
                    results[t]["tp"] += 1
                    matched_gt.add(i)
                    matched = True
                    break
            if not matched:
                results[t]["fp"] += 1

        results[t]["fn"] += len(gts) - len(matched_gt)

    metrics = {}
    for t, c in results.items():
        prec = c["tp"] / (c["tp"] + c["fp"]) if (c["tp"] + c["fp"]) else 0
        rec = c["tp"] / (c["tp"] + c["fn"]) if (c["tp"] + c["fn"]) else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
        metrics[t] = {
            "precision": round(prec, 3),
            "recall": round(rec, 3),
            "f1": round(f1, 3),
            "support": c["tp"] + c["fn"]
        }
    return metrics


if __name__ == "__main__":
    print("Usage: provide predictions.json and ground_truth.json")
    print("Example output will contain per-class precision/recall/F1")
    print("Also run separately on fairness subgroups (dark skin, glasses, low light)")
