/** Hard cap for the power/rank compare chart — more series bury the plot on a phone. */

export const CHART_TEAM_LIMIT = 10;

export type PoweredTeam = {
  team_id: string;
  power?: number | null;
  rank?: number | null;
};

function sortByPower(ids: string[], teams: PoweredTeam[]): string[] {
  const byId = new Map(teams.map((team) => [team.team_id, team]));
  return [...ids].sort((a, b) => {
    const pa = byId.get(a)?.power ?? Number.NEGATIVE_INFINITY;
    const pb = byId.get(b)?.power ?? Number.NEGATIVE_INFINITY;
    if (pb !== pa) return pb - pa;
    return (byId.get(a)?.rank ?? 9999) - (byId.get(b)?.rank ?? 9999);
  });
}

export function topTeamsByPower(
  ids: string[],
  teams: PoweredTeam[],
  limit = CHART_TEAM_LIMIT,
): string[] {
  if (ids.length <= limit) return ids.slice();
  return sortByPower(ids, teams).slice(0, limit);
}

export function addChartTeam(
  current: string[],
  id: string,
  teams: PoweredTeam[],
  limit = CHART_TEAM_LIMIT,
): { next: string[]; dropped: string | null } {
  if (current.includes(id)) {
    return { next: current.filter((x) => x !== id), dropped: null };
  }
  if (current.length < limit) {
    return { next: [...current, id], dropped: null };
  }
  const weakest = sortByPower(current, teams).at(-1) ?? current[0];
  return { next: [...current.filter((x) => x !== weakest), id], dropped: weakest };
}
