import asyncio

from app.schemas.research_papers import IndPaper, SearchResponse
from app.services.research_sources.arxiv import ArxivClient
from app.services.research_sources.dblp import DblpClient
from app.services.research_sources.openalex import OpenAlexClient
from app.services.research_sources.semanticscholar import SemanticScholarClient


# temporarily hardcoded, till we change it to be from user profile
HARDCODED_INTERESTS = [
    "artificial intelligence in healthcare",
    "machine learning and detection of medical conditions",
    "computer vision medical imaging",
]


class ResearchService:
    def __init__(self) -> None:
        self.clients = [
            ArxivClient(),
            OpenAlexClient(),
            SemanticScholarClient(),
            DblpClient(),
        ]

    async def get_research_for_user(self) -> SearchResponse:
        all_results: list[IndPaper] = []

        for interest in HARDCODED_INTERESTS:
            for client in self.clients:
                try:
                    results = await client.search(interest, max_results=5)
                    all_results.extend(results)
                except Exception as error:
                    print(
                        f"Error fetching from {client.__class__.__name__} "
                        f"for query '{interest}': {error}"
                    )
                # lowk just using this for semantic scholar, might be good to get rid of that source
                await asyncio.sleep(1)

        deduped_results = self._dedupe_results(all_results)

        return SearchResponse(
            interests=HARDCODED_INTERESTS,
            total_results=len(deduped_results),
            papers=deduped_results,
        )

    def _dedupe_results(self, papers: list[IndPaper]) -> list[IndPaper]:
        seen_titles = set()
        unique_papers: list[IndPaper] = []

        for paper in papers:
            normalized_title = paper.title.lower().strip()

            if not normalized_title:
                continue

            if normalized_title in seen_titles:
                continue

            seen_titles.add(normalized_title)
            unique_papers.append(paper)

        return unique_papers