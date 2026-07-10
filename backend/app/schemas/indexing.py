from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PreparedChunk(BaseModel):
    """A chunk prepared for embedding and datastore insertion."""

    chunk_id: str
    paper_id: str
    chunk_index: int

    # Original paper text.
    chunk_text: str

    # Text that will be passed to the embedding model.
    embedding_text: str

    metadata: dict[str, Any] = Field(default_factory=dict)