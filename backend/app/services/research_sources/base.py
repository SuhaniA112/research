from abc import ABC, abstractmethod

from app.schemas.research_papers import IndPaper


class ResearchSourceClient(ABC):
    @abstractmethod
    async def search(
        self, query: str, max_results: int = 10, offset: int = 0
    ) -> list[IndPaper]:
        """Return up to ``max_results`` hits, skipping the first ``offset`` (paging)."""
        pass
