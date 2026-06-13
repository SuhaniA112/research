import httpx

from app.schemas.research_papers import IndPaper
from app.services.research_sources.base import ResearchSourceClient

class OpenAlexClient(ResearchSourceClient):
    BASE_URL = "https://api.openalex.org/works"

    async def search(self, query: str, max_results: int = 10) -> list[IndPaper]:
        params = {
            "search": query,
            "per-page": max_results,
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()

        data = response.json()
        results: list[IndPaper] = []

        for item in data.get("results", []):
            authors = []

            for authorship in item.get("authorships", []):
                author = authorship.get("author", {})
                name = author.get("display_name")
                if name:
                    authors.append(name)

            results.append(
                IndPaper(
                    title=item.get("title") or "Untitled",
                    abstract=self._reconstruct_abstract(
                        item.get("abstract_inverted_index")
                    ),
                    authors=authors,
                    year=item.get("publication_year"),
                    url=item.get("id"),
                    pdf_url=(item.get("open_access") or {}).get("oa_url"),
                    source="openalex",
                    external_id=item.get("id"),
                    topics=[query],
                )
            )

        return results

    def _reconstruct_abstract(
        self,
        inverted_index: dict[str, list[int]] | None,
    ) -> str | None:
        if not inverted_index:
            return None

        words_by_position = {}

        for word, positions in inverted_index.items():
            for position in positions:
                words_by_position[position] = word

        return " ".join(
            words_by_position[position]
            for position in sorted(words_by_position)
        )