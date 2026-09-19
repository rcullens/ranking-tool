export type Team = {
  team_id: string;
  name: string;
  district: string;
  region: string;
  classification: string;
  rank: number | null;
  record: string;
  power: number | null;
};

export type Status = {
  provider: string;
  football_window: boolean;
  window_label: string;
  last_sync: string | null;
  last_result: string;
  current_week: number;
  finals: number;
  scheduled: number;
  week_complete: boolean;
  next_window: string;
  updates_last_sync: number;
  feed_url: string | null;
  interval_sec: number;
};

export type RankRow = {
  rank: number;
  team_id: string;
  name: string;
  record: string;
  district: string;
  region: string;
  district_record: string;
  classification: string;
  power: number;
  rank_delta: number | null;
  notes: string;
  low_confidence: boolean;
  local_rank?: number;
  statewide_rank?: number | null;
};

export type Board = {
  id: string;
  label: string;
  kind: "district" | "region";
  team_ids: string[];
  power: RankRow[];
  standings?: RankRow[];
};

export type BoardsResponse = {
  week: number;
  districts: Board[];
  regions: Board[];
};

export type HistoryResponse = {
  weeks: number[];
  history: Record<string, RankRow[]>;
};

export type CompareResponse = {
  metric: string;
  weeks: number[];
  current_week: number;
  series: {
    team_id: string;
    name: string;
    classification: string;
    points: { week: number; value: number | null; rank: number | null }[];
  }[];
};

export const API_BASE_KEY = "sixman_api_base";

export function getStoredApiBase(): string {
  if (typeof localStorage === "undefined") return "";
  return (localStorage.getItem(API_BASE_KEY) || "").trim().replace(/\/$/, "");
}

export function setStoredApiBase(url: string) {
  const cleaned = url.trim().replace(/\/$/, "");
  if (cleaned) localStorage.setItem(API_BASE_KEY, cleaned);
  else localStorage.removeItem(API_BASE_KEY);
}

export function isNativeShell(): boolean {
  const cap = (globalThis as { Capacitor?: { isNativePlatform?: () => boolean } }).Capacitor;
  return Boolean(cap?.isNativePlatform?.());
}

function offlinePath(path: string): string | null {
  const route = path.split("?")[0];
  const map: Record<string, string> = {
    "/api/status": "/offline/status.json",
    "/api/teams": "/offline/teams.json",
    "/api/presets": "/offline/presets.json",
    "/api/rankings": "/offline/rankings.json",
    "/api/boards": "/offline/boards.json",
    "/api/history": "/offline/history.json",
  };
  return map[route] ?? null;
}

async function readJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} failed`);
  return res.json() as Promise<T>;
}

export function compareFromHistory(
  history: HistoryResponse,
  ids: string[],
  metric: "power" | "rank",
): CompareResponse {
  const weeks = history.weeks;
  const series = ids.map((teamId) => {
    let name = teamId;
    let classification = "";
    const points = weeks.map((week) => {
      const row = (history.history[String(week)] || []).find((item) => item.team_id === teamId);
      if (row) {
        name = row.name;
        classification = row.classification;
      }
      return {
        week,
        value: row ? (metric === "rank" ? row.rank : row.power) : null,
        rank: row?.rank ?? null,
      };
    });
    return { team_id: teamId, name, classification, points };
  });
  return {
    metric,
    weeks,
    current_week: weeks.length ? weeks[weeks.length - 1] : 0,
    series,
  };
}

let historyCache: HistoryResponse | null = null;

async function loadHistory(base: string): Promise<HistoryResponse> {
  if (historyCache) return historyCache;
  try {
    if (base || !isNativeShell()) {
      historyCache = await readJson<HistoryResponse>(`${base}/api/history`);
      return historyCache;
    }
  } catch {
    historyCache = null;
  }
  historyCache = await readJson<HistoryResponse>("/offline/history.json");
  return historyCache;
}

async function get<T>(path: string): Promise<T> {
  const base = getStoredApiBase();
  const tryLive = Boolean(base) || !isNativeShell();
  if (tryLive) {
    try {
      return await readJson<T>(`${base}${path}`);
    } catch (err) {
      if (base) throw err instanceof Error ? err : new Error(String(err));
    }
  }
  if (path.startsWith("/api/compare")) {
    const params = new URLSearchParams(path.split("?")[1] || "");
    const ids = (params.get("teams") || "").split(",").filter(Boolean);
    const metric = params.get("metric") === "rank" ? "rank" : "power";
    const history = await loadHistory(base);
    const chosen =
      ids.length > 0
        ? ids
        : ((await readJson<{ presets: Record<string, string[]> }>("/offline/presets.json")).presets
            .last_week_top10 ?? []);
    return compareFromHistory(history, chosen, metric) as T;
  }
  const offline = offlinePath(path);
  if (!offline) throw new Error(`${path} is not available offline`);
  return readJson<T>(offline);
}

export const api = {
  status: () => get<Status>("/api/status"),
  teams: () => get<{ teams: Team[] }>("/api/teams"),
  presets: () => get<{ presets: Record<string, string[]> }>("/api/presets"),
  rankings: () => get<{ week: number; rankings: RankRow[] }>("/api/rankings"),
  boards: () => get<BoardsResponse>("/api/boards"),
  compare: (ids: string[], metric: "power" | "rank") =>
    get<CompareResponse>(`/api/compare?metric=${metric}&teams=${ids.join(",")}`),
  sync: async () => {
    const base = getStoredApiBase();
    const tryLive = Boolean(base) || !isNativeShell();
    if (tryLive) {
      const res = await fetch(`${base}/api/sync`, { method: "POST" });
      if (!res.ok) throw new Error("sync failed");
      historyCache = null;
      return res.json() as Promise<Status>;
    }
    const status = await readJson<Status>("/offline/status.json");
    return { ...status, last_result: "offline snapshot · sync needs a live server URL" };
  },
};
