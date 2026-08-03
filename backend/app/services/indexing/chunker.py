from __future__ import annotations

import re
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.indexing.pdf_extractor import ExtractedPage


@dataclass(frozen=True, slots=True)
class TextChunk:
    chunk_index: int
    text: str
    page_number: int | None = None


class PaperChunker:
    def __init__(
        self,
        chunk_size: int = 2000,
        chunk_overlap: int = 250,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")

        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")

        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=[
                "\n\n",
                "\n",
                ". ",
                " ",
                "",
            ],
            is_separator_regex=False,
        )

    def split(self, content: str | None) -> list[TextChunk]:
        cleaned_content = self._clean_text(content)

        if not cleaned_content:
            return []

        chunk_texts = self._splitter.split_text(cleaned_content)

        return [
            TextChunk(
                chunk_index=index,
                text=chunk_text.strip(),
                page_number=None,
            )
            for index, chunk_text in enumerate(chunk_texts)
            if chunk_text.strip()
        ]

    def split_pages(
        self,
        pages: list[ExtractedPage],
    ) -> list[TextChunk]:
        """
        Split full-paper extracted pages into chunks while preserving page numbers.
        """

        all_chunks: list[TextChunk] = []
        next_chunk_index = 0

        for page in pages:
            cleaned_page_text = self._clean_text(page.text)

            if not cleaned_page_text:
                continue

            page_chunk_texts = self._splitter.split_text(cleaned_page_text)

            for page_chunk_text in page_chunk_texts:
                page_chunk_text = page_chunk_text.strip()

                if not page_chunk_text:
                    continue

                all_chunks.append(
                    TextChunk(
                        chunk_index=next_chunk_index,
                        text=page_chunk_text,
                        page_number=page.page_number,
                    )
                )

                next_chunk_index += 1

        return all_chunks

    @staticmethod
    def _clean_text(content: str | None) -> str:
        if not content:
            return ""

        text = content.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()
