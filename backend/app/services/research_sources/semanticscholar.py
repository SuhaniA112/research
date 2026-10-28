import httpx

from app.schemas.research_papers import IndPaper
from app.services.query_normalization import normalize_topic_list
from app.services.research_sources.base import ResearchSourceClient
from app.services.taxonomy.paper_topics import build_paper_topics


class SemanticScholarClient(ResearchSourceClient):
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    async def search(self, query: str, max_results: int = 10) -> list[IndPaper]:
        params = {
            "query": query,
            "limit": max_results,
            "fields": (
                "title,abstract,authors,year,url,"
                "openAccessPdf,fieldsOfStudy,"
                "citationCount,venue,isOpenAccess,publicationTypes"
            ),
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()

        data = response.json()
        results: list[IndPaper] = []

        for item in data.get("data", []):
            authors = [
                author.get("name")
                for author in item.get("authors", [])
                if author.get("name")
            ]

            open_access_pdf = item.get("openAccessPdf") or {}

            native_topics = [
                field
                for field in (item.get("fieldsOfStudy") or [])
                if isinstance(field, str) and field.strip()
            ]

            # Query is discovery input only — never appended to paper topics.
            provider_topics = normalize_topic_list(native_topics)
            topics = build_paper_topics(provider_topics=provider_topics)

            results.append(
                IndPaper(
                    title=item.get("title") or "Untitled",
                    abstract=item.get("abstract"),
                    authors=authors,
                    year=item.get("year"),
                    url=item.get("url"),
                    pdf_url=open_access_pdf.get("url"),
                    source="semantic_scholar",
                    external_id=item.get("paperId"),
                    topics=topics,
                    source_categories=[],
                    **self._validity_metadata(item),
                )
            )

        return results

    # Venues that host preprints; papers there are not peer-reviewed yet.
    PREPRINT_VENUES = {"arxiv", "arxiv.org", "biorxiv", "medrxiv", "ssrn", "corr"}

    @classmethod
    def _validity_metadata(cls, item: dict) -> dict:
        """Citation count, venue, open-access and peer-review flags for one paper."""
        venue = (item.get("venue") or "").strip() or None
        publication_types = {
            t for t in (item.get("publicationTypes") or []) if isinstance(t, str)
        }

        is_peer_reviewed: bool | None = None
        if venue and venue.lower() in cls.PREPRINT_VENUES:
            is_peer_reviewed = False
        elif publication_types & {"JournalArticle", "Conference"}:
            is_peer_reviewed = True

        is_oa = item.get("isOpenAccess")
        if not isinstance(is_oa, bool):
            is_oa = True if (item.get("openAccessPdf") or {}).get("url") else None

        citation_count = item.get("citationCount")
        return {
            "citation_count": citation_count if isinstance(citation_count, int) else None,
            "venue": venue,
            "is_open_access": is_oa,
            "is_peer_reviewed": is_peer_reviewed,
        }
