import asyncio

from app.core.logging import get_logger
from app.schemas.research_papers import IndPaper, SearchResponse
from app.services.research_sources.arxiv import ArxivClient
from app.services.research_sources.base import ResearchSourceClient
from app.services.research_sources.dblp import DblpClient
from app.services.research_sources.openalex import OpenAlexClient
from app.services.research_sources.semanticscholar import SemanticScholarClient

logger = get_logger(__name__)

# temporarily hardcoded, till we change it to be from user profile
HARDCODED_SEARCH_QUERIES = [
    "artificial intelligence",
    "machine learning ",
    "medical imaging",
]


class ResearchService:
    def __init__(self) -> None:
        self.clients: list[ResearchSourceClient] = [
            ArxivClient(),
            OpenAlexClient(),
            SemanticScholarClient(),
            DblpClient(),
        ]

    async def get_research_for_user(self) -> SearchResponse:
        """Fan out hardcoded interests × providers concurrently.

        Previously each call was sequential with a 1s sleep (very slow). Results
        are still title-deduped the same way; only fetch concurrency changed.
        """
        all_results: list[IndPaper] = []
        lock = asyncio.Lock()

        async def _one(query: str, client: ResearchSourceClient) -> None:
            name = client.__class__.__name__
            try:
                results = await client.search(query, max_results=5)
                async with lock:
                    all_results.extend(results)
            except Exception as error:
                logger.warning(
                    "legacy_provider_failure provider=%s query=%r error=%s",
                    name,
                    query,
                    error,
                )

        await asyncio.gather(
            *[
                _one(query, client)
                for query in HARDCODED_SEARCH_QUERIES
                for client in self.clients
            ]
        )

        deduped_results = self._dedupe_results(all_results)

        return SearchResponse(
            interests=HARDCODED_SEARCH_QUERIES,
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
