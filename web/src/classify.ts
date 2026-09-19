/** Mirror of sixman_rankings.classify — DI vs DII matching in the board UI. */

const DII = /dii|\bd2\b|division\s*ii\b|division\s*2\b/i;
const DI = /\bdi\b|\bd1\b|division\s*i\b|division\s*1\b/i;

export function divisionOf(tag: string): "DI" | "DII" | null {
  if (!tag) return null;
  if (DII.test(tag)) return "DII";
  if (DI.test(tag)) return "DI";
  return null;
}

export function classificationMatches(teamTag: string, query: string): boolean {
  if (!query || !query.trim()) return true;
  const q = query.trim();
  if (teamTag.trim().toLowerCase() === q.toLowerCase()) return true;
  const qDiv = divisionOf(q);
  const tDiv = divisionOf(teamTag);
  return Boolean(qDiv && tDiv && qDiv === tDiv);
}

export function filterRankRows<T extends { classification?: string; district?: string; region?: string }>(
  rows: T[],
  opts: { classification?: string; district?: string; region?: string } = {},
): T[] {
  return rows.filter((row) => {
    if (opts.classification && !classificationMatches(row.classification || "", opts.classification)) {
      return false;
    }
    if (opts.district && (row.district || "") !== opts.district) return false;
    if (opts.region && (row.region || "") !== opts.region) return false;
    return true;
  });
}
