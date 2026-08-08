from __future__ import annotations

from app.schemas.indexing import PreparedChunk
from app.schemas.research_papers import IndPaper
from app.services.indexing.chunker import PaperChunker, TextChunk
from app.services.indexing.pdf_extractor import PdfTextExtractor
from app.services.query_normalization import normalize_topic_list


class PaperIndexer:
    INDEXER_VERSION = "v1"

    def __init__(
        self,
        chunker: PaperChunker | None = None,
        pdf_extractor: PdfTextExtractor | None = None,
    ) -> None:
        self.chunker = chunker or PaperChunker(
            chunk_size=2000,
            chunk_overlap=250,
        )

        self.pdf_extractor = pdf_extractor or PdfTextExtractor()

    async def prepare_chunks(
        self,
        paper_id: str,
        paper: IndPaper,
    ) -> list[PreparedChunk]:
        if not paper_id.strip():
            raise ValueError("paper_id cannot be empty")

        text_chunks, content_type = await self._get_paper_chunks(paper)

        if not text_chunks:
            return []

        topics = normalize_topic_list(list(paper.topics))

        prepared_chunks: list[PreparedChunk] = []

        for chunk in text_chunks:
            chunk_id = (
                f"{paper_id}:" f"{self.INDEXER_VERSION}:" f"{chunk.chunk_index:05d}"
            )

            embedding_text = self._build_embedding_text(
                title=paper.title,
                topics=topics,
                page_number=chunk.page_number,
                chunk_text=chunk.text,
            )

            prepared_chunks.append(
                PreparedChunk(
                    chunk_id=chunk_id,
                    paper_id=paper_id,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.text,
                    embedding_text=embedding_text,
                    metadata={
                        "title": paper.title,
                        "topics": topics,
                        "authors": paper.authors,
                        "year": paper.year,
                        "source": paper.source,
                        "external_id": paper.external_id,
                        "url": paper.url,
                        "pdf_url": paper.pdf_url,
                        "page_number": chunk.page_number,
                        "content_type": content_type,
                        "indexer_version": self.INDEXER_VERSION,
                    },
                )
            )

        return prepared_chunks

    async def _get_paper_chunks(
        self,
        paper: IndPaper,
    ) -> tuple[list[TextChunk], str]:
        if paper.pdf_url:
            try:
                pages = await self.pdf_extractor.extract(paper.pdf_url)

                return (
                    self.chunker.split_pages(pages),
                    "full_text",
                )

            except Exception as error:
                # For development, print this clearly.
                # Later, replace this with your project logger.
                print(f"Full PDF extraction failed for " f"{paper.title!r}: {error}")

        if paper.abstract:
            return (
                self.chunker.split(paper.abstract),
                "abstract",
            )

        # Indexable Text guarantee: a paper is never unembeddable just because its
        # Source Provider has no abstract and no PDF (e.g. DBLP always returns
        # abstract=None) - fall back to the title, which IndPaper always requires.
        return (
            self.chunker.split(paper.title),
            "title",
        )

    @staticmethod
    def _build_embedding_text(
        title: str,
        topics: list[str],
        chunk_text: str,
        page_number: int | None = None,
    ) -> str:
        sections = [
            f"Title: {title.strip()}",
        ]

        if topics:
            sections.append(f"Topics: {', '.join(topics)}")

        if page_number is not None:
            sections.append(f"Page: {page_number}")

        sections.append(f"Content:\n{chunk_text}")

        return "\n\n".join(sections)
