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
  if (!(qDiv && tDiv && qDiv === tDiv)) return false;
  const bareUil = /^(di|dii|d1|d2)$/i.test(q) || /^1a\b/i.test(q);
  if (bareUil) {
    return /^1a\b/i.test(teamTag) && !/tapps|taiao|tcaf|tcal|\bind\b/i.test(teamTag);
  }
  return true;
}

export function filterRankRows<
  T extends { classification?: string; district?: string; region?: string; association?: string },
>(
  rows: T[],
  opts: { classification?: string; district?: string; region?: string; association?: string } = {},
): T[] {
  return rows.filter((row) => {
    if (opts.classification && !classificationMatches(row.classification || "", opts.classification)) {
      return false;
    }
    if (opts.district && (row.district || "") !== opts.district) return false;
    if (opts.region && (row.region || "") !== opts.region) return false;
    if (opts.association && (row.association || "UIL").toUpperCase() !== opts.association.toUpperCase()) {
      return false;
    }
    return true;
  });
}
