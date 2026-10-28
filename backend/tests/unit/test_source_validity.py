"""Source Validity: provider parsing, metadata merging, and project stats."""

from types import SimpleNamespace

from app.models.paper import Paper
from app.repositories.paper_repo import PaperRepository
from app.schemas.research_papers import IndPaper
from app.services.research_sources.dblp import DblpClient
from app.services.research_sources.openalex import OpenAlexClient
from app.services.research_sources.semanticscholar import SemanticScholarClient
from app.services.source_validity import compute_source_validity


def _paper(**kwargs) -> SimpleNamespace:
    defaults = dict(
        authors=["A"],
        citation_count=None,
        is_open_access=None,
        is_peer_reviewed=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# --- compute_source_validity -------------------------------------------------


def test_empty_project_has_no_score() -> None:
    result = compute_source_validity([])
    assert result.score is None
    assert result.status == "NO SOURCES YET"
    assert result.total_sources == 0
    assert [m.percent for m in result.metrics] == [None, None, None, None]


def test_metrics_only_count_papers_with_reported_fields() -> None:
    papers = [
        _paper(authors=["A", "B"], citation_count=12, is_open_access=True, is_peer_reviewed=True),
        _paper(authors=["A"], citation_count=0, is_open_access=False, is_peer_reviewed=False),
        # DBLP-style paper: no citation count or OA info reported.
        _paper(authors=["A", "B", "C"], is_peer_reviewed=True),
        _paper(authors=[]),
    ]
    result = compute_source_validity(papers)
    by_key = {m.key: m for m in result.metrics}

    assert (by_key["cross_cited"].count, by_key["cross_cited"].known) == (1, 2)
    assert by_key["cross_cited"].percent == 50
    assert (by_key["peer_reviewed"].count, by_key["peer_reviewed"].known) == (2, 3)
    assert by_key["peer_reviewed"].percent == 67
    assert by_key["open_access"].percent == 50
    # Paper with no authors is excluded from the denominator.
    assert (by_key["multi_author"].count, by_key["multi_author"].known) == (2, 3)
    assert by_key["multi_author"].percent == 67

    assert result.score == round((50 + 67 + 50 + 67) / 4)
    assert result.total_sources == 4
    assert result.status == "WELL SUPPORTED"


def test_score_ignores_metrics_without_data() -> None:
    papers = [_paper(authors=["A", "B"]), _paper(authors=["A", "B"])]
    result = compute_source_validity(papers)
    assert result.score == 100
    assert result.status == "HIGHLY CONNECTED"
    assert {m.key: m.percent for m in result.metrics}["open_access"] is None


# --- provider parsing --------------------------------------------------------


def test_openalex_journal_article() -> None:
    meta = OpenAlexClient._validity_metadata(
        {
            "type": "article",
            "cited_by_count": 42,
            "open_access": {"is_oa": True},
            "primary_location": {"source": {"display_name": "Nature", "type": "journal"}},
        }
    )
    assert meta == {
        "citation_count": 42,
        "venue": "Nature",
        "is_open_access": True,
        "is_peer_reviewed": True,
    }


def test_openalex_preprint_is_not_peer_reviewed() -> None:
    meta = OpenAlexClient._validity_metadata(
        {
            "type": "preprint",
            "primary_location": {"source": {"display_name": "arXiv", "type": "repository"}},
        }
    )
    assert meta["is_peer_reviewed"] is False
    assert meta["citation_count"] is None
    assert meta["is_open_access"] is None


def test_semantic_scholar_arxiv_venue_overrides_publication_type() -> None:
    meta = SemanticScholarClient._validity_metadata(
        {
            "venue": "arXiv.org",
            "publicationTypes": ["JournalArticle"],
            "citationCount": 3,
            "isOpenAccess": True,
        }
    )
    assert meta["is_peer_reviewed"] is False
    assert meta["citation_count"] == 3


def test_semantic_scholar_conference_and_pdf_fallback() -> None:
    meta = SemanticScholarClient._validity_metadata(
        {
            "venue": "NeurIPS",
            "publicationTypes": ["Conference"],
            "openAccessPdf": {"url": "https://x/y.pdf"},
        }
    )
    assert meta["is_peer_reviewed"] is True
    assert meta["is_open_access"] is True


def test_dblp_corr_is_unreviewed_and_conference_is_reviewed() -> None:
    corr = DblpClient._validity_metadata(
        {"venue": "CoRR", "type": "Informal and Other Publications", "access": "open"}
    )
    assert corr["is_peer_reviewed"] is False
    assert corr["is_open_access"] is True

    conf = DblpClient._validity_metadata(
        {"venue": ["ICML", "PMLR"], "type": "Conference and Workshop Papers"}
    )
    assert conf["is_peer_reviewed"] is True
    assert conf["venue"] == "ICML, PMLR"
    assert conf["is_open_access"] is None


# --- merging on upsert -------------------------------------------------------


def _ind(**kwargs) -> IndPaper:
    return IndPaper(title="T", source="openalex", external_id="x", **kwargs)


def test_validity_updates_keep_known_values_and_take_upgrades() -> None:
    existing = Paper(
        source="openalex",
        external_id="x",
        title="T",
        citation_count=10,
        venue="arXiv",
        is_open_access=True,
        is_peer_reviewed=False,
    )
    updates = PaperRepository._validity_updates(
        existing,
        _ind(
            citation_count=5,  # lower → ignored
            venue="ICLR",  # replaces the arXiv placeholder
            is_open_access=False,  # never revokes OA
            is_peer_reviewed=True,  # preprint later published
        ),
    )
    assert updates == {"venue": "ICLR", "is_peer_reviewed": True}


def test_validity_updates_fill_missing_and_ignore_none() -> None:
    existing = Paper(source="openalex", external_id="x", title="T")
    assert PaperRepository._validity_updates(existing, _ind()) == {}
    updates = PaperRepository._validity_updates(
        existing, _ind(citation_count=7, is_open_access=False)
    )
    assert updates == {"citation_count": 7, "is_open_access": False}
