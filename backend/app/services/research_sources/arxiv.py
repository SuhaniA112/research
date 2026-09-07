import feedparser
import httpx

from app.schemas.research_papers import IndPaper
from app.services.research_sources.base import ResearchSourceClient
from app.services.taxonomy.paper_topics import (
    build_paper_topics,
    normalize_source_categories,
)


class ArxivClient(ResearchSourceClient):
    BASE_URL = "https://export.arxiv.org/api/query"

    async def search(self, query: str, max_results: int = 10) -> list[IndPaper]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
        }

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()

        feed = feedparser.parse(response.text)
        results: list[IndPaper] = []

        for entry in feed.entries:
            authors = [
                author.name
                for author in getattr(entry, "authors", [])
                if getattr(author, "name", None)
            ]

            pdf_url = None
            for link in getattr(entry, "links", []):
                if link.get("type") == "application/pdf":
                    pdf_url = link.get("href")

            year = None
            if getattr(entry, "published", None):
                try:
                    year = int(entry.published[:4])
                except ValueError:
                    year = None

            # Query is discovery input only — never copied into paper topics.
            source_categories = normalize_source_categories(
                [
                    tag.term
                    for tag in getattr(entry, "tags", [])
                    if getattr(tag, "term", None)
                ]
            )
            topics = build_paper_topics(source_categories=source_categories)

            results.append(
                IndPaper(
                    title=entry.title.replace("\n", " ").strip(),
                    abstract=entry.summary.replace("\n", " ").strip(),
                    authors=authors,
                    year=year,
                    url=entry.link,
                    pdf_url=pdf_url,
                    source="arxiv",
                    external_id=entry.id.split("/")[-1],
                    topics=topics,
                    source_categories=source_categories,
                )
            )

        return results
