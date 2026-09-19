import { filterRankRows } from "./classify";

export type Team = {
  team_id: string;
  name: string;
  district: string;
  region: string;
  classification: string;
  association?: string;
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
  association?: string;
  power: number;
  rank_delta: number | null;
  power_delta?: number | null;
  notes: string;
  low_confidence: boolean;
  confidence?: number;
  sos?: number;
  density?: number;
  local_rank?: number;
  statewide_rank?: number | null;
};

export type WhatIfResponse = {
  provisional: boolean;
  writes_back: boolean;
  through_week: number;
  game: {
    home_id: string;
    away_id: string;
    home_score: number | null;
    away_score: number | null;
    week: number;
    neutral: boolean;
    district_game: boolean;
  };
  movers: {
    team_id: string;
    name: string;
    rank_before: number | null;
    rank_after: number;
    rank_delta: number | null;
    power_before: number | null;
    power_after: number;
    power_delta: number;
  }[];
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

/** Respect Vite `base` so GitHub Pages (`/ranking-tool/`) and Capacitor (`./`) both resolve. */
export function publicUrl(path: string): string {
  const root = import.meta.env.BASE_URL || "./";
  return `${root}${path.replace(/^\//, "")}`;
}

let snapshotBust = "";

/** Force the next offline reads to skip a stale Pages/CDN cache. */
export function bustOfflineCache() {
  snapshotBust = `v=${Date.now()}`;
  historyCache = null;
  sameOriginLive = null;
}

function offlineCacheQuery(): string {
  return snapshotBust || `v=${Math.floor(Date.now() / 60_000)}`;
}

function offlinePath(path: string): string | null {
  const route = path.split("?")[0];
  const map: Record<string, string> = {
    "/api/status": "offline/status.json",
    "/api/teams": "offline/teams.json",
    "/api/presets": "offline/presets.json",
    "/api/rankings": "offline/rankings.json",
    "/api/boards": "offline/boards.json",
    "/api/history": "offline/history.json",
  };
  const rel = map[route];
  if (!rel) return null;
  return `${publicUrl(rel)}?${offlineCacheQuery()}`;
}

function liveRequired(action: string): Error {
  return new Error(`${action} needs a live sixman-rank serve URL (Phone / APK).`);
}

async function readJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`${url} failed (${res.status})`);
  const text = await res.text();
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`${url} is not JSON`);
  }
}

let sameOriginLive: Promise<boolean> | null = null;

/** True when this origin still serves the Python FastAPI (not a static Vercel host). */
export async function sameOriginHasApi(): Promise<boolean> {
  if (sameOriginLive) return sameOriginLive;
  sameOriginLive = (async () => {
    try {
      const data = await readJson<{ current_week?: unknown }>(publicUrl("api/status"));
      return typeof data.current_week === "number";
    } catch {
      return false;
    }
  })();
  return sameOriginLive;
}

async function shouldTrySameOrigin(): Promise<boolean> {
  if (getStoredApiBase()) return false;
  if (isNativeShell()) return false;
  return sameOriginHasApi();
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
    if (base) {
      historyCache = await readJson<HistoryResponse>(`${base}/api/history`);
      return historyCache;
    }
    if (await shouldTrySameOrigin()) {
      historyCache = await readJson<HistoryResponse>(publicUrl("api/history"));
      return historyCache;
    }
  } catch {
    historyCache = null;
  }
  historyCache = await readJson<HistoryResponse>(publicUrl("offline/history.json"));
  return historyCache;
}

async function get<T>(path: string): Promise<T> {
  const base = getStoredApiBase();
  if (base) {
    return readJson<T>(`${base}${path}`);
  }
  if (await shouldTrySameOrigin()) {
    try {
      return await readJson<T>(publicUrl(path));
    } catch {
      /* static host or stale API — fall through to bundled snapshots */
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
        : ((await readJson<{ presets: Record<string, string[]> }>(publicUrl("offline/presets.json"))).presets
            .last_week_top10 ?? []);
    return compareFromHistory(history, chosen, metric) as T;
  }
  const offline = offlinePath(path);
  if (!offline) throw new Error(`${path} is not available offline`);
  const payload = await readJson<T>(offline);
  if (path.split("?")[0] === "/api/rankings") {
    const params = new URLSearchParams(path.split("?")[1] || "");
    const body = payload as { rankings?: RankRow[] };
    const rankings = filterRankRows(body.rankings || [], {
      classification: params.get("classification") || undefined,
      district: params.get("district") || undefined,
      region: params.get("region") || undefined,
      association: params.get("association") || undefined,
    });
    return { ...body, rankings, classification: params.get("classification") } as T;
  }
  return payload;
}

async function postLive<T>(path: string, body: unknown, action: string): Promise<T> {
  const base = getStoredApiBase();
  if (!base && !(await shouldTrySameOrigin())) throw liveRequired(action);
  const res = await fetch(`${base}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) {
    let detail = `${action} failed`;
    try {
      const err = (await res.json()) as { detail?: string };
      if (err.detail) detail = String(err.detail);
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  historyCache = null;
  return res.json() as Promise<T>;
}

export const api = {
  status: () => get<Status>("/api/status"),
  teams: () => get<{ teams: Team[] }>("/api/teams"),
  presets: () => get<{ presets: Record<string, string[]> }>("/api/presets"),
  rankings: (opts?: {
    classification?: string;
    district?: string;
    region?: string;
    association?: string;
  }) => {
    const params = new URLSearchParams();
    if (opts?.classification) params.set("classification", opts.classification);
    if (opts?.district) params.set("district", opts.district);
    if (opts?.region) params.set("region", opts.region);
    if (opts?.association) params.set("association", opts.association);
    const q = params.toString();
    return get<{ week: number; rankings: RankRow[] }>(`/api/rankings${q ? `?${q}` : ""}`);
  },
  boards: () => get<BoardsResponse>("/api/boards"),
  compare: (ids: string[], metric: "power" | "rank") =>
    get<CompareResponse>(`/api/compare?metric=${metric}&teams=${ids.join(",")}`),
  sync: async () => {
    const base = getStoredApiBase();
    const tryLive = Boolean(base) || (await shouldTrySameOrigin());
    if (tryLive) {
      const res = await fetch(`${base}/api/sync`, { method: "POST" });
      if (!res.ok) throw new Error("sync failed");
      historyCache = null;
      return res.json() as Promise<Status>;
    }
    // Static Pages: pull the cron-published snapshot (same live pipeline, no PC).
    bustOfflineCache();
    const status = await readJson<Status>(publicUrl(`offline/status.json?${snapshotBust}`));
    return {
      ...status,
      last_result: status.last_result || "pulled latest GitHub Pages snapshot",
    };
  },
  ingest: (payload: unknown) => postLive<{ ok: boolean; updates: number }>("/api/ingest", payload, "Ingest"),
  whatIf: (payload: {
    home_id: string;
    away_id: string;
    home_score?: number;
    away_score?: number;
    margin?: number;
    neutral?: boolean;
    district_game?: boolean;
  }) => postLive<WhatIfResponse>("/api/what-if", payload, "What-if"),
};
