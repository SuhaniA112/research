# PaperSearcher

Helps a user discover, save, and reason over academic papers pulled from external research APIs.

## Language

**Source Provider**:
One of the four external metadata APIs the backend queries for papers: Arxiv, OpenAlex, Semantic Scholar, DBLP.
_Avoid_: scraper, web scraping

**Ingestion**:
The process of pulling paper results from a Source Provider and persisting them to the database. Distinct from scraping — Source Providers return structured metadata, not raw HTML/PDF bytes.
_Avoid_: scraping, crawling

**Indexable Text**:
The text of a paper that gets embedded into the vector store. In v1, this is title + abstract only. Full paper text (from PDF) is a deferred, later extension of this concept — the schema and indexer must not assume abstract-only is permanent.
_Avoid_: document text, content

**Chunk**:
A unit of Indexable Text that gets embedded as a single vector. A paper has one or more chunks. In v1 every paper has exactly one chunk (its abstract); multi-chunk splitting is deferred until full-text papers exist.
_Avoid_: segment, passage

**Discovery**:
Fetching new papers the user hasn't seen yet by querying the Source Providers live with the user's stated interests. Existing mechanism (`research_service.py`); not vector-based, not part of the Retriever.
_Avoid_: search, retrieval

**Retrieval**:
Finding the most relevant already-ingested Chunks for a user's question via vector similarity, to ground an AI-generated answer. Operates only over the database, never calls Source Providers directly.
_Avoid_: search, discovery, lookup

**Save**:
The user action of attaching a paper (found via Discovery) to one of their Projects. This is the trigger for Ingestion — a paper is not persisted, chunked, or embedded until it's saved. Papers surfaced by Discovery but never saved are never ingested.
_Avoid_: bookmark, add
