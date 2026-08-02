from typing import Literal

import httpx


class VoyageEmbeddingClient:
    BASE_URL = "https://api.voyageai.com/v1/embeddings"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def embed(
        self, texts: list[str], *, input_type: Literal["query", "document"]
    ) -> list[list[float]]:
        payload = {
            "model": self.model,
            "input": texts,
            "input_type": input_type,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self.BASE_URL, json=payload, headers=headers)
            response.raise_for_status()

        data = response.json()
        by_index = {item["index"]: item["embedding"] for item in data["data"]}
        return [by_index[i] for i in range(len(texts))]
