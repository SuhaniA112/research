import httpx

from app.schemas.research_papers import IndPaper
from app.services.query_normalization import normalize_topic_list
from app.services.research_sources.base import ResearchSourceClient
from app.services.taxonomy.paper_topics import build_paper_topics


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
            authors: list[str] = []

            for authorship in item.get("authorships", []):
                author = authorship.get("author", {})
                name = author.get("display_name")
                if name:
                    authors.append(name)

            native_topics: list[str] = []

            # Prefer OpenAlex topics, which are more specific than legacy concepts.
            for topic in item.get("topics") or []:
                display_name = topic.get("display_name")

                if display_name:
                    native_topics.append(display_name)

            # Fall back to concepts only when OpenAlex returned no topics.
            if not native_topics:
                for concept in item.get("concepts") or []:
                    display_name = concept.get("display_name")

                    if display_name:
                        native_topics.append(display_name)

            # Query is discovery input only — never appended to paper topics.
            provider_topics = normalize_topic_list(native_topics)
            topics = build_paper_topics(provider_topics=provider_topics)

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
                    topics=topics,
                    source_categories=[],
                    **self._validity_metadata(item),
                )
            )

        return results

    @staticmethod
    def _validity_metadata(item: dict) -> dict:
        """Citation count, venue, open-access and peer-review flags for one work."""
        primary_source = (item.get("primary_location") or {}).get("source") or {}
        source_type = (primary_source.get("type") or "").lower()
        work_type = (item.get("type") or "").lower()

        is_peer_reviewed: bool | None = None
        if work_type == "preprint" or source_type == "repository":
            is_peer_reviewed = False
        elif source_type in {"journal", "conference"}:
            is_peer_reviewed = True

        citation_count = item.get("cited_by_count")
        is_oa = (item.get("open_access") or {}).get("is_oa")

        return {
            "citation_count": citation_count if isinstance(citation_count, int) else None,
            "venue": primary_source.get("display_name") or None,
            "is_open_access": is_oa if isinstance(is_oa, bool) else None,
            "is_peer_reviewed": is_peer_reviewed,
        }

    def _reconstruct_abstract(
        self,
        inverted_index: dict[str, list[int]] | None,
    ) -> str | None:
        if not inverted_index:
            return None

        words_by_position: dict[int, str] = {}

        for word, positions in inverted_index.items():
            for position in positions:
                words_by_position[position] = word

        return " ".join(
            words_by_position[position]
            for position in sorted(words_by_position)
        )
