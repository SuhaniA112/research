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
                "openAccessPdf,fieldsOfStudy"
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
                )
            )

        return results
