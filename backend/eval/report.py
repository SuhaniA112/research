"""Render eval + diagnostics JSON as one self-contained HTML report.

Usage: npm run eval:report [-- --run <json> --diagnostics <json>]
"""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"

SERIES = ["#2563eb", "#d97706", "#059669", "#db2777", "#7c3aed", "#0891b2", "#65a30d", "#dc2626"]
MUTED = "#9ca3af"

W, H = 560, 260
PAD_L, PAD_R, PAD_T, PAD_B = 44, 12, 12, 34


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def fmt(value, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


# --- tiny SVG chart helpers ---------------------------------------------------


def _frame(inner: str, y_ticks: list[tuple[float, str]], x_label: str = "", y_label: str = "") -> str:
    plot_h = H - PAD_T - PAD_B
    grid = "".join(
        f'<line x1="{PAD_L}" x2="{W - PAD_R}" y1="{PAD_T + plot_h * (1 - f):.1f}" '
        f'y2="{PAD_T + plot_h * (1 - f):.1f}" class="grid"/>'
        f'<text x="{PAD_L - 6}" y="{PAD_T + plot_h * (1 - f) + 4:.1f}" class="tick" text-anchor="end">{esc(label)}</text>'
        for f, label in y_ticks
    )
    labels = ""
    if x_label:
        labels += f'<text x="{(PAD_L + W - PAD_R) / 2}" y="{H - 4}" class="axis" text-anchor="middle">{esc(x_label)}</text>'
    if y_label:
        labels += (
            f'<text transform="translate(11,{(PAD_T + H - PAD_B) / 2}) rotate(-90)" '
            f'class="axis" text-anchor="middle">{esc(y_label)}</text>'
        )
    return f'<svg viewBox="0 0 {W} {H}" role="img">{grid}{inner}{labels}</svg>'


def _unit_ticks() -> list[tuple[float, str]]:
    return [(f, f"{f:.2g}") for f in (0, 0.25, 0.5, 0.75, 1.0)]


def _legend(names: list[str], colors: list[str]) -> str:
    return '<div class="legend">' + "".join(
        f'<span><i style="background:{c}"></i>{esc(n)}</span>' for n, c in zip(names, colors)
    ) + "</div>"


def grouped_bars(categories: list[str], series: dict[str, list[float]], y_label: str = "") -> str:
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    group_w = plot_w / max(len(categories), 1)
    bar_w = group_w * 0.8 / max(len(series), 1)
    parts = []
    for gi, cat in enumerate(categories):
        x0 = PAD_L + gi * group_w + group_w * 0.1
        for si, (name, values) in enumerate(series.items()):
            v = max(0.0, min(1.0, values[gi]))
            h = plot_h * v
            parts.append(
                f'<rect x="{x0 + si * bar_w:.1f}" y="{PAD_T + plot_h - h:.1f}" width="{bar_w - 2:.1f}" '
                f'height="{h:.1f}" fill="{SERIES[si % len(SERIES)]}"><title>{esc(name)} @ {esc(cat)}: {v:.3f}</title></rect>'
            )
        parts.append(
            f'<text x="{x0 + group_w * 0.4:.1f}" y="{H - PAD_B + 14}" class="tick" text-anchor="middle">{esc(cat)}</text>'
        )
    return _frame("".join(parts), _unit_ticks(), y_label=y_label) + _legend(
        list(series), SERIES[: len(series)]
    )


def line_chart(
    xs: list[float],
    series: dict[str, list[float]],
    *,
    x_range: tuple[float, float],
    x_label: str,
    y_label: str = "",
    marker_x: float | None = None,
    marker_label: str = "",
) -> str:
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    lo, hi = x_range
    span = (hi - lo) or 1.0

    def px(x: float) -> float:
        return PAD_L + plot_w * (x - lo) / span

    def py(y: float) -> float:
        return PAD_T + plot_h * (1 - max(0.0, min(1.0, y)))

    parts = []
    for si, (name, ys) in enumerate(series.items()):
        color = SERIES[si % len(SERIES)]
        pts = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in zip(xs, ys))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
        parts.extend(
            f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="2.5" fill="{color}"><title>{esc(name)} {x:g}: {y:.3f}</title></circle>'
            for x, y in zip(xs, ys)
        )
    if marker_x is not None:
        parts.append(
            f'<line x1="{px(marker_x):.1f}" x2="{px(marker_x):.1f}" y1="{PAD_T}" y2="{PAD_T + plot_h}" class="marker"/>'
            f'<text x="{px(marker_x) + 4:.1f}" y="{PAD_T + 12}" class="tick">{esc(marker_label)}</text>'
        )
    integer_axis = all(float(x).is_integer() for x in (*xs, lo, hi)) and span <= 12
    tick_xs = (
        list(range(int(lo), int(hi) + 1))
        if integer_axis
        else [lo + span * i / 5 for i in range(6)]
    )
    for x in tick_xs:
        parts.append(f'<text x="{px(x):.1f}" y="{H - PAD_B + 14}" class="tick" text-anchor="middle">{x:.2g}</text>')
    return _frame("".join(parts), _unit_ticks(), x_label=x_label, y_label=y_label) + _legend(
        list(series), SERIES[: len(series)]
    )


def histogram_chart(hists: dict[str, dict], x_label: str) -> str:
    """Overlaid histograms, each normalised to share of its own total."""
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    first = next(iter(hists.values()))
    edges = first["edges"]
    n_bins = len(edges) - 1
    shares = {}
    for name, h in hists.items():
        total = sum(h["counts"]) or 1
        shares[name] = [c / total for c in h["counts"]]
    top = max((max(s) for s in shares.values()), default=1) or 1
    bin_w = plot_w / n_bins
    parts = []
    for si, (name, s) in enumerate(shares.items()):
        color = SERIES[si % len(SERIES)]
        for bi, share in enumerate(s):
            h = plot_h * share / top
            parts.append(
                f'<rect x="{PAD_L + bi * bin_w:.1f}" y="{PAD_T + plot_h - h:.1f}" width="{bin_w - 1:.1f}" '
                f'height="{h:.1f}" fill="{color}" fill-opacity="0.55">'
                f"<title>{esc(name)} [{edges[bi]}, {edges[bi + 1]}): {share:.1%}</title></rect>"
            )
    for bi in range(0, n_bins + 1, max(1, n_bins // 6)):
        parts.append(
            f'<text x="{PAD_L + bi * bin_w:.1f}" y="{H - PAD_B + 14}" class="tick" text-anchor="middle">{edges[bi]:.2g}</text>'
        )
    ticks = [(f, f"{f * top:.0%}") for f in (0, 0.5, 1.0)]
    return _frame("".join(parts), ticks, x_label=x_label, y_label="share") + _legend(
        list(shares), SERIES[: len(shares)]
    )


def scatter_chart(points: list[dict]) -> str:
    if not points:
        return '<p class="empty">Need at least two papers to project.</p>'
    size = 420
    pad = 16
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    x_lo, x_hi = min(xs), max(xs)
    y_lo, y_hi = min(ys), max(ys)
    sx = (size - 2 * pad) / ((x_hi - x_lo) or 1)
    sy = (size - 2 * pad) / ((y_hi - y_lo) or 1)

    topic_counts: dict[str, int] = {}
    for p in points:
        topic_counts[p["topic"]] = topic_counts.get(p["topic"], 0) + 1
    top_topics = sorted(topic_counts, key=topic_counts.get, reverse=True)[: len(SERIES) - 1]
    color_of = {t: SERIES[i] for i, t in enumerate(top_topics)}

    dots = "".join(
        f'<circle cx="{pad + (p["x"] - x_lo) * sx:.1f}" cy="{size - pad - (p["y"] - y_lo) * sy:.1f}" r="5" '
        f'fill="{color_of.get(p["topic"], MUTED)}" fill-opacity="0.8">'
        f'<title>{esc(p["title"])} — {esc(p["topic"])} ({p["chunks"]} chunk(s))</title></circle>'
        for p in points
    )
    names = top_topics + (["other"] if len(topic_counts) > len(top_topics) else [])
    colors = [color_of[t] for t in top_topics] + ([MUTED] if len(names) > len(top_topics) else [])
    return f'<svg viewBox="0 0 {size} {size}" class="square" role="img">{dots}</svg>' + _legend(names, colors)


# --- report sections ----------------------------------------------------------


def tile(label: str, value: str, hint: str = "") -> str:
    return (
        f'<div class="tile"><div class="tile-label">{esc(label)}</div>'
        f'<div class="tile-value">{esc(value)}</div><div class="tile-hint">{esc(hint)}</div></div>'
    )


def retrieval_section(run: dict) -> str:
    s = run["summary"]
    ks = run["ks"]
    tiles = "".join(
        [
            tile("MRR", fmt(s["mrr"]), "mean 1 / rank of first relevant"),
            tile("MAP", fmt(s["map"]), "mean average precision"),
            tile(f"Recall@{ks[-1]}", fmt(s[f"recall@{ks[-1]}"])),
            tile(f"nDCG@{ks[-1]}", fmt(s[f"ndcg@{ks[-1]}"])),
            tile("Gated hit", f"{s['gated_hit']:.0%}", f"distance ≤ {run['settings']['retrieval_max_distance']}"),
        ]
    )
    bars = grouped_bars(
        [f"@{k}" for k in ks],
        {
            "Precision": [s[f"precision@{k}"] for k in ks],
            "Recall": [s[f"recall@{k}"] for k in ks],
            "nDCG": [s[f"ndcg@{k}"] for k in ks],
            "Hit": [s[f"hit@{k}"] for k in ks],
        },
    )
    curve = run.get("pr_curve") or []
    pr = line_chart(
        [p["k"] for p in curve],
        {"Precision": [p["precision"] for p in curve], "Recall": [p["recall"] for p in curve]},
        x_range=(1, max(len(curve), 2)),
        x_label="cutoff k",
    ) if curve else ""

    rows = []
    for q in run["queries"]:
        m = q["metrics"]
        top = q["ranked"][0] if q["ranked"] else None
        if top:
            top_cell = (
                esc(top["title"])
                + (" ✓" if top["relevant"] else "")
                + f' <span class=muted>({top["similarity"]:.2f})</span>'
            )
        else:
            top_cell = "—"
        unreviewed = "" if q["reviewed"] else " <span class=badge>unreviewed</span>"
        rows.append(
            "<tr>"
            f"<td>{esc(q['id'])}{unreviewed}</td>"
            f"<td>{esc(q['question'])}</td>"
            f"<td class=num>{fmt(m['first_relevant_rank'])}</td>"
            f"<td class=num>{fmt(m['rr'], 2)}</td>"
            f"<td>{'✓' if q['gated_hit'] else '✗'}</td>"
            f"<td>{top_cell}</td>"
            "</tr>"
        )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>ID</th><th>Question</th><th>First relevant rank</th>'
        "<th>RR</th><th>Gated</th><th>Top result (similarity)</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )

    gen = run.get("generation")
    gen_html = ""
    if gen:
        gen_html = (
            '<h3>Generation</h3><div class="tiles">'
            + tile("Citation validity", f"{gen['citation_validity']:.0%}", "citations inside retrieved set")
            + tile("False refusals", str(len(gen["false_refusals"])), ", ".join(gen["false_refusals"]))
            + tile("Possibly hallucinated", str(len(gen["possibly_hallucinated"])), ", ".join(gen["possibly_hallucinated"]))
            + "</div>"
        )

    return (
        f"<section><h2>Retrieval quality</h2>"
        f"<p class=muted>{len(run['queries'])} golden queries · project {esc(run['project_id'])} · "
        f"{esc(run['embedding_model'])} · {esc(run['created_at'][:19])}Z</p>"
        f'<div class="tiles">{tiles}</div>'
        f'<div class="grid2"><figure><figcaption>Metrics by cutoff</figcaption>{bars}</figure>'
        f"<figure><figcaption>Precision / recall vs k</figcaption>{pr}</figure></div>"
        f"<h3>Per query</h3>{table}{gen_html}</section>"
    )


def diagnostics_section(d: dict) -> str:
    a = d["anisotropy"]
    h = d["hubness"]
    sep = d.get("golden_separation")
    tiles = [
        tile("Chunks / papers", f"{d['num_chunks']} / {d['num_papers']}", f"{d['dimension']}-d {d['embedding_model']}"),
        tile("Mean norm", fmt(d["norms"]["mean"]), f"range {fmt(d['norms']['min'])}–{fmt(d['norms']['max'])}"),
        tile("Anisotropy", fmt(a["mean_pairwise_cosine"]), "mean pairwise cosine (0 = isotropic)"),
        tile("Effective dims", fmt(d["effective_dim"], 1), "participation ratio"),
        tile("Hubness skew", fmt(h["skewness"], 2), f"top hub in {h['max_share']:.0%} of {h['k']}-NN lists"),
    ]
    if sep:
        tiles.append(tile("Relevance ROC AUC", fmt(sep["roc_auc"]), "query→paper similarity"))
    figures = [
        f"<figure><figcaption>Pairwise cosine similarity between chunks</figcaption>"
        f"{histogram_chart({'chunk pairs': d['pairwise_cosine_hist']}, 'cosine similarity')}</figure>",
        f"<figure><figcaption>Explained variance, top principal components</figcaption>"
        f"{grouped_bars([f'PC{i + 1}' for i in range(len(d['explained_variance_top10']))], {'variance share': d['explained_variance_top10']})}</figure>",
    ]
    if sep:
        sweep = sep["threshold_sweep"]
        figures.append(
            f"<figure><figcaption>Query→paper similarity: relevant vs irrelevant</figcaption>"
            f"{histogram_chart({'relevant': sep['relevant_hist'], 'irrelevant': sep['irrelevant_hist']}, 'cosine similarity')}</figure>"
        )
        figures.append(
            f"<figure><figcaption>Distance gate sweep (Ask keeps chunks with distance ≤ gate)</figcaption>"
            + line_chart(
                [r["distance_threshold"] for r in sweep],
                {
                    "Precision": [r["precision"] for r in sweep],
                    "Recall": [r["recall"] for r in sweep],
                    "F1": [r["f1"] for r in sweep],
                },
                x_range=(0.0, 1.0),
                x_label="cosine distance gate",
                marker_x=sep["current_distance_gate"],
                marker_label="current",
            )
            + "</figure>"
        )
    scatter = scatter_chart(d.get("paper_projection") or [])
    hub_note = f"<p class=muted>Biggest hub: {esc(h['top_hub_paper'])}</p>" if h.get("top_hub_paper") else ""
    return (
        f"<section><h2>Embedding diagnostics</h2>"
        f"<p class=muted>{'project ' + esc(d['project_id']) if d['project_id'] else 'all chunks'} · "
        f"{esc(d['created_at'][:19])}Z</p>"
        f'<div class="tiles">{"".join(tiles)}</div>{hub_note}'
        f'<div class="grid2">{"".join(figures)}</div>'
        f"<figure><figcaption>Papers in 2-D (PCA of chunk centroids), coloured by first topic</figcaption>{scatter}</figure>"
        f"</section>"
    )


STYLE = """
:root{--bg:#fff;--fg:#111827;--muted:#6b7280;--line:#e5e7eb;--card:#f9fafb}
@media (prefers-color-scheme:dark){:root{--bg:#0b0f17;--fg:#e5e7eb;--muted:#9ca3af;--line:#1f2937;--card:#111827}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 48px}h1{margin:0 0 4px;font-size:22px}
h2{font-size:18px;margin:32px 0 4px}h3{font-size:15px;margin:20px 0 8px}
.muted{color:var(--muted)}.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px;margin:12px 0}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.tile-label{font-size:12px;color:var(--muted)}.tile-value{font-size:22px;font-weight:600;font-variant-numeric:tabular-nums}
.tile-hint{font-size:11px;color:var(--muted)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,480px),1fr));gap:16px}
figure{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}
figcaption{font-weight:600;margin-bottom:6px}svg{width:100%;height:auto;display:block}
svg.square{max-width:460px;margin:0 auto}
.grid{stroke:var(--line)}.tick{fill:var(--muted);font-size:10px}.axis{fill:var(--muted);font-size:11px}
.marker{stroke:var(--fg);stroke-dasharray:4 3}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12px;color:var(--muted);margin-top:6px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
td.num{text-align:right;font-variant-numeric:tabular-nums}.badge{font-size:10px;border:1px solid var(--line);border-radius:6px;padding:0 4px;color:var(--muted)}
.empty{color:var(--muted)}.table-wrap{overflow-x:auto}
"""


def tuning_section(t: dict) -> str:
    k = t["k"]
    rows = "".join(
        f"<tr><td>{esc(name)}</td><td class=num>{fmt(m[f'ndcg@{k}'])}</td>"
        f"<td class=num>{fmt(m['mrr'])}</td><td class=num>{fmt(m[f'recall@{k}'])}</td></tr>"
        for name, m in t["metrics"].items()
    )
    table = (
        f'<div class="table-wrap"><table><thead><tr><th>Ranking</th><th>nDCG@{k}</th>'
        f"<th>MRR</th><th>Recall@{k}</th></tr></thead><tbody>{rows}</tbody></table></div>"
    )
    names = list(t["weights"]["tuned"])
    bars = grouped_bars(
        names,
        {label: [t["weights"][label].get(n, 0.0) for n in names] for label in ("current", "tuned")},
    )
    return (
        "<section><h2>Relevance model tuning</h2>"
        f"<p class=muted>{t['n_queries']} golden queries x {t['n_candidates']} candidates · "
        f"grid step {t['step']} · leave-one-out row is the honest estimate</p>"
        f"{table}<figure><figcaption>Feature weights</figcaption>{bars}</figure></section>"
    )


def render(run: dict | None, diagnostics: dict | None, tuning: dict | None = None) -> str:
    body = []
    if run:
        body.append(retrieval_section(run))
    if diagnostics:
        body.append(diagnostics_section(diagnostics))
    if tuning:
        body.append(tuning_section(tuning))
    if not body:
        body.append('<p class="empty">No results yet. Run <code>npm run eval</code> and/or '
                    "<code>npm run eval:diagnostics</code> first.</p>")
    return (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width,initial-scale=1">'
        f"<title>Retrieval Eval Report</title><style>{STYLE}</style></head><body><main>"
        "<h1>PaperSearcher retrieval report</h1>"
        '<p class="muted">Ranking metrics over the golden set and diagnostics of the embedding space.</p>'
        + "".join(body)
        + "</main></body></html>"
    )


def latest(pattern: str) -> Path | None:
    files = sorted(RESULTS_DIR.glob(pattern))
    return files[-1] if files else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--run", type=Path, default=None, help="run_eval.py JSON (default: latest)")
    parser.add_argument("--diagnostics", type=Path, default=None, help="diagnose_embeddings.py JSON (default: latest)")
    parser.add_argument("--out", type=Path, default=RESULTS_DIR / "report.html")
    args = parser.parse_args()

    run_path = args.run or latest("run-*.json")
    diag_path = args.diagnostics or latest("diagnostics-*.json")
    run = json.loads(run_path.read_text(encoding="utf-8")) if run_path else None
    diagnostics = json.loads(diag_path.read_text(encoding="utf-8")) if diag_path else None
    tune_path = latest("tuning-*.json")
    tuning = json.loads(tune_path.read_text(encoding="utf-8")) if tune_path else None

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(run, diagnostics, tuning), encoding="utf-8")
    print(f"Wrote {args.out}" + (f"\n  run: {run_path}" if run_path else "") + (f"\n  diagnostics: {diag_path}" if diag_path else ""))


if __name__ == "__main__":
    main()
