/** Truncate text to `maxWords` words, appending an ellipsis when shortened. */
export function truncateWords(text: string, maxWords = 50): string {
  const trimmed = text.trim();
  if (!trimmed) return "";
  const words = trimmed.split(/\s+/);
  if (words.length <= maxWords) return trimmed;
  return `${words.slice(0, maxWords).join(" ")}…`;
}

const NAMED_ENTITIES: Record<string, string> = {
  amp: "&",
  lt: "<",
  gt: ">",
  quot: '"',
  apos: "'",
  nbsp: " ",
};

/**
 * Decode HTML entities in provider titles/abstracts
 * (e.g. `&quot;Hey Siri...&quot;` → `"Hey Siri..."`).
 */
export function decodeHtmlEntities(text: string | null | undefined): string {
  if (!text) return "";
  const withNumeric = text
    .replace(/&#x([0-9a-fA-F]+);/g, (_, hex: string) =>
      String.fromCodePoint(Number.parseInt(hex, 16)),
    )
    .replace(/&#(\d+);/g, (_, dec: string) =>
      String.fromCodePoint(Number.parseInt(dec, 10)),
    );
  return withNumeric
    .replace(/&([a-zA-Z]+);/g, (match, name: string) => NAMED_ENTITIES[name] ?? match)
    .replace(/\u00a0/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
