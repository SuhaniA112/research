import httpx

from app.schemas.research_papers import IndPaper
from app.services.research_sources.base import ResearchSourceClient

class SemanticScholarClient(ResearchSourceClient):
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    async def search(self, query: str, max_results: int = 10) -> list[IndPaper]:
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,authors,year,url,openAccessPdf",
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
                    topics=[query],
                )
            )

        return results