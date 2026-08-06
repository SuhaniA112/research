"""Tests for HTML entity cleanup in paper text."""

from app.core.text import clean_paper_text
from app.schemas.research_papers import IndPaper


def test_clean_paper_text_decodes_quot() -> None:
    raw = "&quot;Hey Siri, How Am I Doing?&quot;: Legal Challenges for Artificial Intelligence Alter Egos in Healthcare."
    assert (
        clean_paper_text(raw)
        == '"Hey Siri, How Am I Doing?": Legal Challenges for Artificial Intelligence Alter Egos in Healthcare.'
    )


def test_ind_paper_cleans_title_on_construct() -> None:
    paper = IndPaper(
        title="&quot;Hey Siri&quot; &amp; friends",
        abstract="A &lt;b&gt;test&lt;/b&gt; abstract",
        source="semanticscholar",
        external_id="abc",
    )
    assert paper.title == '"Hey Siri" & friends'
    assert paper.abstract == "A <b>test</b> abstract"
