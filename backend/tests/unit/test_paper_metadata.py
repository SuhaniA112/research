from app.models.paper import Paper
from app.repositories.paper_repo import PaperRepository
from app.schemas.research_papers import IndPaper


def test_better_metadata_does_not_overwrite_with_empty() -> None:
    existing = Paper(
        source="arxiv",
        external_id="x",
        title="Full Title",
        abstract="Long abstract text",
        authors=["A", "B"],
        year=2020,
        url="https://example.com",
        pdf_url="https://example.com/a.pdf",
        topics=["ml"],
    )
    incoming = IndPaper(
        title="",
        abstract=None,
        authors=[],
        year=None,
        url=None,
        pdf_url=None,
        source="arxiv",
        external_id="x",
        topics=[],
    )
    updates = PaperRepository._better_metadata_updates(existing, incoming)
    assert updates == {}


def test_better_metadata_upgrades_abstract() -> None:
    existing = Paper(
        source="arxiv",
        external_id="x",
        title="Title",
        abstract=None,
        authors=[],
        year=None,
        url=None,
        pdf_url=None,
        topics=[],
    )
    incoming = IndPaper(
        title="Title",
        abstract="Now we have an abstract",
        authors=["A"],
        year=2021,
        url="https://example.com",
        source="arxiv",
        external_id="x",
    )
    updates = PaperRepository._better_metadata_updates(existing, incoming)
    assert updates["abstract"] == "Now we have an abstract"
    assert updates["year"] == 2021
    assert updates["authors"] == ["A"]


def test_better_metadata_merges_topics() -> None:
    existing = Paper(
        source="arxiv",
        external_id="x",
        title="Title",
        abstract="Abstract",
        authors=["A"],
        year=2020,
        url="https://example.com",
        pdf_url=None,
        topics=["Machine Learning", "NLP"],
    )
    incoming = IndPaper(
        title="Title",
        abstract="Abstract",
        authors=["A"],
        year=2020,
        url="https://example.com",
        source="arxiv",
        external_id="x",
        topics=["machine learning, Computer Vision"],
    )
    updates = PaperRepository._better_metadata_updates(existing, incoming)
    assert updates["topics"] == [
        "Machine Learning",
        "NLP",
        "Computer Vision",
    ]


def test_better_metadata_keeps_existing_topics_when_incoming_shorter() -> None:
    existing = Paper(
        source="arxiv",
        external_id="x",
        title="Title",
        abstract="Abstract",
        authors=["A"],
        year=2020,
        url="https://example.com",
        pdf_url=None,
        topics=["Machine Learning", "Medical Imaging", "Cancer Detection"],
    )
    incoming = IndPaper(
        title="Title",
        abstract="Abstract",
        authors=["A"],
        year=2020,
        url="https://example.com",
        source="arxiv",
        external_id="x",
        topics=["Machine Learning"],
    )
    updates = PaperRepository._better_metadata_updates(existing, incoming)
    assert "topics" not in updates
