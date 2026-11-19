/** Frappe stores assignments on documents in `_assign` as a JSON array of user ids. */

export function assigneeFromTask(assignField?: string | null): string {
  if (!assignField) return "";
  try {
    const parsed = JSON.parse(assignField);
    if (Array.isArray(parsed) && parsed.length > 0) return String(parsed[0]);
  } catch {
    return "";
  }
  return "";
}

export function assignJsonForUser(userId?: string | null): string {
  if (!userId) return "[]";
  return JSON.stringify([userId]);
}
