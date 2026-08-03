export type ResultOrigin = "database" | "external" | "database_and_external";

export type TopicMatchType = "exact" | "semantic" | "new";

export type CacheMissReason =
  | "no_matching_topic"
  | "no_relevant_papers"
  | "insufficient_results"
  | "low_similarity"
  | "stale_topic"
  | "force_refresh"
  | "incomplete_metadata";

export interface DiscoveryPaper {
  id: string;
  source: string;
  external_id: string;
  title: string;
  abstract: string | null;
  authors: string[];
  year: number | null;
  url: string | null;
  pdf_url: string | null;
  topics: string[];
  created_at: string;
}

export interface DiscoverySearchRequest {
  query: string;
  limit?: number;
  force_refresh?: boolean;
}

export interface ProviderFailure {
  provider: string;
  failure_type: string;
  detail?: string | null;
}

export interface DiscoverySearchResultItem {
  paper: DiscoveryPaper;
  similarity_score: number | null;
  result_origin: ResultOrigin;
}

export interface DiscoverySearchResponse {
  query: string;
  normalized_query: string;
  search_execution_id: string;
  matched_topic_id: string;
  topic_match_type: TopicMatchType;
  cache_hit: boolean;
  cache_miss_reason: CacheMissReason | null;
  external_search_performed: boolean;
  providers_attempted: string[];
  providers_succeeded: string[];
  providers_failed: ProviderFailure[];
  results: DiscoverySearchResultItem[];
}
