/** Truncate text to `maxWords` words, appending an ellipsis when shortened. */
export function truncateWords(text: string, maxWords = 50): string {
  const trimmed = text.trim();
  if (!trimmed) return "";
  const words = trimmed.split(/\s+/);
  if (words.length <= maxWords) return trimmed;
  return `${words.slice(0, maxWords).join(" ")}…`;
}
