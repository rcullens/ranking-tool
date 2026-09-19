/** Mirror of sixman_rankings.classify — UIL DI/DII plus association filters. */

const DIII = /diii|\bd3\b|division\s*iii\b|division\s*3\b/i;
const DII = /dii|\bd2\b|division\s*ii\b|division\s*2\b/i;
const DI = /\bdi\b|\bd1\b|division\s*i\b|division\s*1\b/i;
const ASSOCS = ["UIL", "TAPPS", "TAIAO", "TCAF", "TCAL", "IND"] as const;

export function associationOf(tag: string): string {
  const t = (tag || "").toUpperCase();
  for (const prefix of ASSOCS) {
    if (prefix !== "UIL" && t.startsWith(prefix)) return prefix;
  }
  return "UIL";
}

export function divisionOf(tag: string): "DI" | "DII" | "DIII" | null {
  if (!tag) return null;
  if (DIII.test(tag)) return "DIII";
  if (DII.test(tag)) return "DII";
  if (DI.test(tag)) return "DI";
  return null;
}

export function classificationMatches(teamTag: string, query: string): boolean {
  if (!query || !query.trim()) return true;
  const q = query.trim();
  if (teamTag.trim().toLowerCase() === q.toLowerCase()) return true;
  const qUpper = q.toUpperCase();
  if ((ASSOCS as readonly string[]).includes(qUpper)) {
    return associationOf(teamTag) === qUpper;
  }
  const qDiv = divisionOf(q);
  const tDiv = divisionOf(teamTag);
  if (qDiv && tDiv && qDiv === tDiv) {
    if (/^(di|dii|diii|d1|d2|d3)$/i.test(q)) {
      return associationOf(teamTag) === "UIL";
    }
    return associationOf(teamTag) === associationOf(q);
  }
  return false;
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
