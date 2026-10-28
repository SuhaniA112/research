"""The HTML eval report renders from synthetic results without a database."""

import re
import xml.etree.ElementTree as ET

import numpy as np

from eval import embedding_diagnostics as diag
from eval import metrics
from eval.report import render


def sample_run() -> dict:
    queries = []
    ranked_for_curve = []
    for qi, (ranked, relevant) in enumerate(
        [(["p1", "p2", "p3"], {"p1"}), (["p2", "p3", "p1"], {"p3"}), (["p3", "p2", "p1"], {"p9"})]
    ):
        queries.append(
            {
                "id": f"g{qi + 1}",
                "question": f"Question <{qi}> & co?",
                "reviewed": qi != 2,
                "relevant": sorted(relevant),
                "gated_hit": qi == 0,
                "metrics": metrics.evaluate_query(ranked, relevant, (1, 3)),
                "ranked": [
                    {"paper_id": p, "title": f"Paper {p}", "similarity": 0.8 - 0.1 * i, "relevant": p in relevant}
                    for i, p in enumerate(ranked)
                ],
            }
        )
        ranked_for_curve.append((ranked, relevant))
    summary = metrics.aggregate([q["metrics"] for q in queries])
    summary["gated_hit"] = 1 / 3
    return {
        "created_at": "2026-10-28T00:00:00+00:00",
        "project_id": "proj",
        "embedding_model": "voyage-test",
        "ks": [1, 3],
        "settings": {"retrieval_max_distance": 0.4, "retrieval_top_k": 5},
        "summary": summary,
        "pr_curve": metrics.precision_recall_curve(ranked_for_curve, 3),
        "generation": {"citation_validity": 1.0, "false_refusals": [], "possibly_hallucinated": ["g3"]},
        "queries": queries,
    }


def sample_diagnostics() -> dict:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(60, 16))
    proj = diag.pca(x)
    pos, neg = rng.uniform(0.5, 0.9, 20), rng.uniform(0.1, 0.6, 80)
    return {
        "created_at": "2026-10-28T00:00:00+00:00",
        "project_id": None,
        "embedding_model": "voyage-test",
        "num_chunks": 60,
        "num_papers": 6,
        "dimension": 16,
        "norms": diag.norm_stats(x),
        "anisotropy": diag.anisotropy(x),
        "pairwise_cosine_hist": diag.histogram(diag.pairwise_cosine_sample(x)),
        "effective_dim": proj["effective_dim"],
        "explained_variance_top10": proj["explained_variance_ratio"][:10].tolist(),
        "hubness": {**diag.hubness(x, k=5), "top_hub_paper": "Hub & Spoke"},
        "paper_projection": [
            {"paper_id": str(i), "title": f"P{i}", "topic": "NLP" if i % 2 else "Vision",
             "x": float(proj["projection"][i, 0]), "y": float(proj["projection"][i, 1]), "chunks": 3}
            for i in range(6)
        ],
        "golden_separation": {
            "roc_auc": diag.roc_auc(pos, neg),
            "relevant_hist": diag.histogram(pos),
            "irrelevant_hist": diag.histogram(neg),
            "threshold_sweep": diag.threshold_sweep(pos, neg),
            "current_distance_gate": 0.4,
        },
    }


def test_report_renders_all_sections_with_valid_svg() -> None:
    page = render(sample_run(), sample_diagnostics())
    for text in ("Retrieval quality", "Embedding diagnostics", "MRR", "Relevance ROC AUC", "unreviewed"):
        assert text in page
    # User text is escaped.
    assert "Question &lt;0&gt; &amp; co?" in page
    assert "Hub &amp; Spoke" in page
    svgs = re.findall(r"<svg.*?</svg>", page, flags=re.S)
    assert len(svgs) >= 6
    for svg in svgs:
        ET.fromstring(svg)  # well-formed


def test_report_renders_tuning_section() -> None:
    m = {"ndcg@10": 0.5, "mrr": 0.4, "recall@10": 0.9}
    tuning = {
        "k": 10, "step": 0.1, "n_queries": 5, "n_candidates": 20,
        "metrics": {"baseline (vector similarity only)": m, "tuned (leave-one-out)": m},
        "weights": {"current": {"search": 0.5, "topic": 0.5}, "tuned": {"search": 1.0, "topic": 0.0}},
    }
    page = render(None, None, tuning)
    assert "Relevance model tuning" in page and "leave-one-out" in page
    for svg in re.findall(r"<svg.*?</svg>", page, flags=re.S):
        ET.fromstring(svg)


def test_report_renders_empty_state() -> None:
    assert "No results yet" in render(None, None)
