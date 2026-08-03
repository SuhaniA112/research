from __future__ import annotations

from dataclasses import dataclass

import httpx
import pymupdf


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    page_number: int
    text: str


class PdfTextExtractor:
    """Downloads a PDF and extracts readable text from each page."""

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        max_pdf_size_bytes: int = 30_000_000,
    ) -> None:
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_pdf_size_bytes = max_pdf_size_bytes

    async def extract(self, pdf_url: str) -> list[ExtractedPage]:
        if not pdf_url.strip():
            raise ValueError("pdf_url cannot be empty")

        pdf_bytes = await self._download_pdf(pdf_url)

        document = pymupdf.open(
            stream=pdf_bytes,
            filetype="pdf",
        )

        try:
            pages: list[ExtractedPage] = []

            for page_index in range(document.page_count):
                page = document.load_page(page_index)

                # sort=True generally produces a more natural reading order.
                text = page.get_text(
                    "text",
                    sort=True,
                ).strip()

                if not text:
                    continue

                pages.append(
                    ExtractedPage(
                        # Human-readable page numbering starts at 1.
                        page_number=page_index + 1,
                        text=text,
                    )
                )

            if not pages:
                raise ValueError("The PDF contained no extractable text")

            return pages

        finally:
            document.close()

    async def _download_pdf(self, pdf_url: str) -> bytes:
        async with httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=True,
        ) as client:
            response = await client.get(pdf_url)
            response.raise_for_status()

        pdf_bytes = response.content

        if not pdf_bytes:
            raise ValueError("Downloaded PDF was empty")

        if len(pdf_bytes) > self._max_pdf_size_bytes:
            raise ValueError("Downloaded PDF exceeds the configured size limit")

        content_type = response.headers.get(
            "content-type",
            "",
        ).lower()

        # Some servers do not send the right Content-Type,
        # so also check the PDF file signature.
        is_pdf_content_type = "application/pdf" in content_type
        has_pdf_signature = pdf_bytes.startswith(b"%PDF")

        if not is_pdf_content_type and not has_pdf_signature:
            raise ValueError(
                f"URL did not return a PDF. " f"Content-Type was {content_type!r}"
            )

        return pdf_bytes
