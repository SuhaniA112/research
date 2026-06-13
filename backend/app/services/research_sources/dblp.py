import httpx

from app.schemas.research_papers import IndPaper
from app.services.research_sources.base import ResearchSourceClient

class DblpClient(ResearchSourceClient):
    BASE_URL = "https://dblp.org/search/publ/api"

    async def search(self, query: str, max_results: int = 10) -> list[IndPaper]:
        params = {
            "q": query,
            "format": "json",
            "h": max_results,
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()

        data = response.json()
        hits = data.get("result", {}).get("hits", {}).get("hit", [])

        results: list[IndPaper] = []

        for hit in hits:
            info = hit.get("info", {})

            authors = self._extract_authors(info)

            year = None
            if info.get("year"):
                try:
                    year = int(info["year"])
                except ValueError:
                    year = None

            results.append(
                IndPaper(
                    title=info.get("title") or "Untitled",
                    abstract=None,
                    authors=authors,
                    year=year,
                    url=info.get("url"),
                    pdf_url=None,
                    source="dblp",
                    external_id=hit.get("@id"),
                    topics=[query],
                )
            )

        return results

    def _extract_authors(self, info: dict) -> list[str]:
        authors_data = info.get("authors", {}).get("author", [])

        if isinstance(authors_data, dict):
            name = authors_data.get("text")
            return [name] if name else []

        if isinstance(authors_data, list):
            return [
                author.get("text")
                for author in authors_data
                if author.get("text")
            ]

        return []