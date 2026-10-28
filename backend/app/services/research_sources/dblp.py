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
                    # DBLP does not return trustworthy topic metadata here.
                    # An empty list is more truthful than using the search query.
                    topics=[],
                    source_categories=[],
                    **self._validity_metadata(info),
                )
            )

        return results

    PEER_REVIEWED_TYPES = {"Journal Articles", "Conference and Workshop Papers"}
    UNREVIEWED_TYPES = {"Informal and Other Publications", "Informal Publications"}

    @classmethod
    def _validity_metadata(cls, info: dict) -> dict:
        """Venue, open-access and peer-review flags. DBLP has no citation counts."""
        venue = info.get("venue")
        if isinstance(venue, list):
            venue = ", ".join(v for v in venue if isinstance(v, str))
        venue = venue.strip() if isinstance(venue, str) and venue.strip() else None

        pub_type = info.get("type")
        is_peer_reviewed: bool | None = None
        if pub_type in cls.PEER_REVIEWED_TYPES and venue != "CoRR":
            is_peer_reviewed = True
        elif pub_type in cls.UNREVIEWED_TYPES or venue == "CoRR":
            is_peer_reviewed = False

        access = info.get("access")
        is_oa = {"open": True, "closed": False}.get(access) if isinstance(access, str) else None

        return {
            "citation_count": None,
            "venue": venue,
            "is_open_access": is_oa,
            "is_peer_reviewed": is_peer_reviewed,
        }

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
