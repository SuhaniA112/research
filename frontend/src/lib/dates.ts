/** Whole calendar days between `date` and today in the local timezone. */
export function calendarDaysAgo(date: string | Date): number {
  const updated = typeof date === "string" ? new Date(date) : date;
  if (Number.isNaN(updated.getTime())) return 0;

  const now = new Date();
  const startOfToday = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfUpdated = Date.UTC(
    updated.getFullYear(),
    updated.getMonth(),
    updated.getDate(),
  );
  return Math.max(0, Math.floor((startOfToday - startOfUpdated) / 86_400_000));
}

export function formatUpdatedAgo(updatedAt: string | Date): string {
  const days = calendarDaysAgo(updatedAt);
  if (days === 0) return "Updated today";
  if (days === 1) return "Updated 1 day ago";
  return `Updated ${days} days ago`;
}
