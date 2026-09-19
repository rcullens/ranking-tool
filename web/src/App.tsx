import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  api,
  getStoredApiBase,
  isNativeShell,
  setStoredApiBase,
  type Board,
  type CompareResponse,
  type RankRow,
  type Status,
  type Team,
} from "./api";
import { BoardSwitcher, RankingBoards, type BoardView } from "./Boards";
import { classificationMatches } from "./classify";
import { COLORS } from "./lib/utils";
import { BoardTools } from "./Tools";

const PRESET_LABELS: Record<string, string> = {
  last_week_top10: "Last week's Top 10",
  this_week_top10: "This week's Top 10",
  undefeated: "Undefeated",
  division_di: "Division I",
  division_dii: "Division II",
};

const REGION_LABELS: Record<string, string> = {
  "west-texas": "West Texas",
  "trans-pecos": "Trans-Pecos",
  "rolling-plains": "Rolling Plains",
  panhandle: "Panhandle / South Plains",
  "north-central": "North Central",
  "central-east-south": "Central / East / South",
};

function prettyPlace(raw: string) {
  return REGION_LABELS[raw] ?? raw.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function sameIdSet(a: string[], b: string[]) {
  if (a.length !== b.length) return false;
  const left = new Set(a);
  return b.every((id) => left.has(id));
}

function chipLabel(key: string) {
  if (PRESET_LABELS[key]) return PRESET_LABELS[key];
  if (key.startsWith("district:")) return key.replace("district:", "");
  if (key.startsWith("region:")) return prettyPlace(key.replace("region:", ""));
  return key;
}

function chipClass(active: boolean, variant: "named" | "district" | "region" | "clear") {
  const base =
    "min-h-9 touch-manipulation rounded-full border px-3 py-2 text-xs leading-tight";
  if (variant === "clear") {
    return `${base} border-transparent text-stone-500 underline decoration-stone-400`;
  }
  if (active) {
    return `${base} border-stone-900 bg-stone-900 text-white shadow-sm`;
  }
  if (variant === "district") {
    return `${base} border-dashed border-stone-300 text-stone-600`;
  }
  if (variant === "region") {
    return `${base} border-dashed border-stone-400 text-stone-600`;
  }
  return `${base} border-stone-300 bg-white text-stone-700`;
}

export default function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [presets, setPresets] = useState<Record<string, string[]>>({});
  const [rows, setRows] = useState<RankRow[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [metric, setMetric] = useState<"power" | "rank">("power");
  const [compare, setCompare] = useState<CompareResponse | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [view, setView] = useState<BoardView>("statewide");
  const [districts, setDistricts] = useState<Board[]>([]);
  const [regions, setRegions] = useState<Board[]>([]);
  const [districtSort, setDistrictSort] = useState<"power" | "standings">("power");
  const [settingsOpen, setSettingsOpen] = useState(() => isNativeShell());
  const [apiBaseDraft, setApiBaseDraft] = useState(getStoredApiBase);
  const [classFilter, setClassFilter] = useState("");
  const selectedRef = useRef<string[]>([]);
  const clearedRef = useRef(false);
  const metricRef = useRef(metric);
  const teamListRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    selectedRef.current = selected;
  }, [selected]);

  useEffect(() => {
    metricRef.current = metric;
  }, [metric]);

  const refresh = useCallback(async () => {
    const [st, teamPayload, presetPayload, rankPayload, boardPayload] = await Promise.all([
      api.status(),
      api.teams(),
      api.presets(),
      api.rankings(classFilter ? { classification: classFilter } : undefined),
      api.boards(),
    ]);
    setStatus(st);
    setTeams(teamPayload.teams);
    setPresets(presetPayload.presets);
    setRows(rankPayload.rankings);
    setDistricts(boardPayload.districts);
    setRegions(boardPayload.regions);
    const fallback =
      presetPayload.presets.last_week_top10?.length
        ? presetPayload.presets.last_week_top10
        : (presetPayload.presets.this_week_top10 ?? []);
    setSelected((cur) => {
      if (clearedRef.current) return cur;
      if (cur.length) return cur;
      selectedRef.current = fallback;
      return fallback;
    });
    const ids = selectedRef.current;
    if (ids.length) {
      setCompare(await api.compare(ids, metricRef.current));
    }
  }, [classFilter]);

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, [refresh]);

  useEffect(() => {
    if (!selected.length) {
      setCompare(null);
      return;
    }
    api.compare(selected, metric).then(setCompare).catch((err: Error) => setError(err.message));
  }, [selected, metric]);

  useEffect(() => {
    const ms = Math.max(8, status?.interval_sec ?? 20) * 1000;
    const timer = window.setInterval(() => {
      refresh().catch(() => undefined);
    }, ms);
    return () => window.clearInterval(timer);
  }, [refresh, status?.interval_sec]);

  const chartRows = useMemo(() => {
    if (!compare) return [];
    return compare.weeks.map((week) => {
      const point: Record<string, number | string> = { week: `Wk ${week}` };
      for (const series of compare.series) {
        const hit = series.points.find((p) => p.week === week);
        if (hit?.value != null) point[series.team_id] = hit.value;
      }
      return point;
    });
  }, [compare]);

  const namedPresets = Object.entries(presets).filter(
    ([key]) => !key.startsWith("district:") && !key.startsWith("region:"),
  );
  const districtPresets = Object.entries(presets).filter(([key]) => key.startsWith("district:"));
  const regionPresets = Object.entries(presets).filter(([key]) => key.startsWith("region:"));

  const activePresetKey = useMemo(() => {
    if (!selected.length) return null;
    const hit = Object.entries(presets).find(([, ids]) => sameIdSet(selected, ids));
    return hit?.[0] ?? null;
  }, [selected, presets]);

  const filteredTeams = useMemo(() => {
    const q = query.trim().toLowerCase();
    const scopedIds = !q && activePresetKey ? presets[activePresetKey] ?? [] : null;
    const scope = scopedIds ? new Set(scopedIds) : null;
    const rows = teams.filter((team) => {
      if (scope && !scope.has(team.team_id)) return false;
      if (!q) return true;
      const blob = `${team.name} ${team.district} ${team.region} ${team.classification}`.toLowerCase();
      return blob.includes(q);
    });
    if (scopedIds) {
      const order = new Map(scopedIds.map((id, i) => [id, i]));
      rows.sort((a, b) => (order.get(a.team_id) ?? 9999) - (order.get(b.team_id) ?? 9999));
    }
    return rows;
  }, [teams, query, activePresetKey, presets]);

  const focusBoardId =
    activePresetKey?.startsWith("district:")
      ? activePresetKey.replace("district:", "")
      : activePresetKey?.startsWith("region:")
        ? activePresetKey.replace("region:", "")
        : undefined;

  async function onSync() {
    setSyncing(true);
    try {
      await api.sync();
      await refresh();
    } finally {
      setSyncing(false);
    }
  }

  function selectIds(ids: string[]) {
    clearedRef.current = ids.length === 0;
    const next = ids.slice();
    selectedRef.current = next;
    setSelected(next);
    requestAnimationFrame(() => teamListRef.current?.scrollTo({ top: 0 }));
  }

  function applyPreset(key: string, ids: string[]) {
    selectIds(ids);
    setQuery("");
    if (key === "division_di") {
      setClassFilter("DI");
      setView("statewide");
    } else if (key === "division_dii") {
      setClassFilter("DII");
      setView("statewide");
    } else if (key.startsWith("district:")) {
      setClassFilter("");
      setView("districts");
    } else if (key.startsWith("region:")) {
      setClassFilter("");
      setView("regions");
    } else {
      setClassFilter("");
      setView("statewide");
    }
  }

  function clearCompare() {
    clearedRef.current = true;
    selectedRef.current = [];
    setSelected([]);
    setQuery("");
    setClassFilter("");
  }

  function toggle(id: string) {
    clearedRef.current = false;
    setSelected((cur) => {
      const next = cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id];
      selectedRef.current = next;
      return next;
    });
  }

  const yReverse = metric === "rank";
  const statewideRows = classFilter
    ? rows.filter((row) => classificationMatches(row.classification, classFilter))
    : rows;

  return (
    <div className="min-h-screen px-4 py-6 md:px-8">
      <header className="mx-auto flex max-w-7xl flex-col gap-3 border-b border-stone-300 pb-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-stone-500">Texas UIL Six-Man</p>
          <h1 className="font-sans text-3xl tracking-tight text-stone-900 md:text-4xl">
            Live power rankings
          </h1>
          <p className="mt-1 max-w-xl text-sm text-stone-600">
            Every UIL 1A six-man program (Division I and II) is ranked from #1 to last,
            including Aquilla. Live MaxPreps / SixManFootball finals land on this board
            via GitHub Actions — no laptop required. Search the full list, or load last
            week&apos;s Top 10.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              status?.football_window
                ? "bg-emerald-100 text-emerald-800"
                : "bg-stone-200 text-stone-700"
            }`}
          >
            {status?.football_window
              ? `Live window · ${status.window_label}`
              : "Off-window · waiting for Thu"}
          </span>
          <span className="rounded-full bg-white px-3 py-1 text-xs text-stone-600 shadow-sm">
            Week {status?.current_week ?? "—"}
            {status?.week_complete ? " published" : " in progress"}
          </span>
          <button
            type="button"
            onClick={onSync}
            disabled={syncing}
            className="rounded-md bg-stone-900 px-3 py-1.5 text-sm text-white disabled:opacity-60"
          >
            {syncing ? "Syncing…" : "Sync scores now"}
          </button>
          <button
            type="button"
            onClick={() => setSettingsOpen((open) => !open)}
            className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm text-stone-700"
          >
            Phone / APK
          </button>
        </div>
      </header>

      {settingsOpen ? (
        <div className="mx-auto mt-3 max-w-7xl rounded-xl border border-stone-200 bg-white p-4 text-sm shadow-sm">
          <h2 className="font-semibold text-stone-900">Use from a phone (no PC)</h2>
          <p className="mt-1 text-stone-600">
            This HTTPS site <strong>is</strong> the live phone board. GitHub Actions
            pulls MaxPreps / SixManFootball scores on Thursday, Friday, and Saturday
            (America/Chicago), reranks the full UIL field, and republishes these
            snapshots. Tap <strong>Sync scores now</strong> to fetch the latest Pages
            JSON — no PC. What-if / ingest still need an optional{" "}
            <code className="rounded bg-stone-100 px-1">sixman-rank serve</code> URL.
          </p>
          <ol className="mt-3 list-decimal space-y-1 pl-5 text-stone-600">
            <li>On a Pixel, open <strong>https://rcullens.github.io/ranking-tool/</strong> in <strong>Chrome</strong> (not the in-app browser).</li>
            <li>Chrome menu (⋮) → <strong>Install app</strong> or <strong>Add to Home screen</strong>.</li>
            <li>Launch <strong>Six-Man</strong> from the home-screen icon. Boards and charts work offline after that first load.</li>
            <li>Optional APK: download <code className="rounded bg-stone-100 px-1">app-debug.apk</code> from the GitHub Release on rcullens/ranking-tool, then Settings → Install unknown apps → Chrome → Install.</li>
          </ol>
          <label className="mt-3 block text-xs font-medium uppercase tracking-wide text-stone-500">
            Live server URL (optional)
          </label>
          <div className="mt-1 flex flex-col gap-2 sm:flex-row">
            <input
              value={apiBaseDraft}
              onChange={(e) => setApiBaseDraft(e.target.value)}
              placeholder="http://192.168.1.20:43127"
              className="min-w-0 flex-1 rounded-md border border-stone-300 px-2 py-1.5"
            />
            <button
              type="button"
              className="rounded-md bg-stone-900 px-3 py-1.5 text-white"
              onClick={() => {
                setStoredApiBase(apiBaseDraft);
                window.location.reload();
              }}
            >
              Save
            </button>
            <button
              type="button"
              className="rounded-md border border-stone-300 px-3 py-1.5"
              onClick={() => {
                setStoredApiBase("");
                window.location.reload();
              }}
            >
              Use bundled data
            </button>
          </div>
          <p className="mt-2 text-xs text-stone-500">
            Leave blank to stay on the cron-updated Pages snapshots (the live phone
            path). Paste a <code className="rounded bg-stone-100 px-1">sixman-rank serve</code>{" "}
            URL only if you want on-device what-if and webhook ingest.
          </p>
        </div>
      ) : null}

      {error ? <p className="mx-auto mt-3 max-w-7xl text-sm text-red-700">{error}</p> : null}

      <p className="mx-auto mt-2 max-w-7xl text-xs text-stone-500">
        {status?.last_result ?? "Loading…"}
        {status?.last_sync ? ` · last pull ${new Date(status.last_sync).toLocaleString()}` : ""}
        {status?.provider ? ` · ${status.provider}` : ""}
      </p>

      <main className="mx-auto mt-6 grid max-w-7xl gap-6 lg:grid-cols-[280px_1fr]">
        <aside className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Compare</h2>
            <div className="flex rounded-md bg-stone-100 p-0.5 text-xs">
              <button
                type="button"
                className={`rounded px-2 py-1 ${metric === "power" ? "bg-white shadow-sm" : ""}`}
                onClick={() => setMetric("power")}
              >
                Power
              </button>
              <button
                type="button"
                className={`rounded px-2 py-1 ${metric === "rank" ? "bg-white shadow-sm" : ""}`}
                onClick={() => setMetric("rank")}
              >
                Rank
              </button>
            </div>
          </div>
          <div className="relative z-10 mb-3 flex flex-wrap gap-2">
            {namedPresets.map(([key, ids]) => {
              const active = activePresetKey === key;
              return (
                <button
                  key={key}
                  type="button"
                  aria-pressed={active}
                  onClick={() => applyPreset(key, ids)}
                  className={chipClass(active, "named")}
                >
                  {chipLabel(key)}
                </button>
              );
            })}
            {districtPresets.map(([key, ids]) => {
              const active = activePresetKey === key;
              return (
                <button
                  key={key}
                  type="button"
                  aria-pressed={active}
                  onClick={() => applyPreset(key, ids)}
                  className={chipClass(active, "district")}
                >
                  {chipLabel(key)}
                </button>
              );
            })}
            {regionPresets.map(([key, ids]) => {
              const active = activePresetKey === key;
              return (
                <button
                  key={key}
                  type="button"
                  aria-pressed={active}
                  onClick={() => applyPreset(key, ids)}
                  className={chipClass(active, "region")}
                >
                  {chipLabel(key)}
                </button>
              );
            })}
            <button
              type="button"
              onClick={clearCompare}
              className={chipClass(false, "clear")}
            >
              Clear
            </button>
          </div>
          {activePresetKey && !query.trim() ? (
            <p className="mb-2 text-xs text-stone-600">
              Showing {chipLabel(activePresetKey)} · {filteredTeams.length} team
              {filteredTeams.length === 1 ? "" : "s"}
            </p>
          ) : null}
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search Aquilla, district, region…"
            className="mb-2 w-full rounded-md border border-stone-300 px-2 py-1.5 text-sm"
          />
          <ul ref={teamListRef} className="max-h-[28rem] space-y-1 overflow-auto text-sm">
            {filteredTeams.map((team) => {
              const on = selected.includes(team.team_id);
              return (
                <li key={team.team_id}>
                  <label className="flex min-h-10 cursor-pointer items-center gap-2 rounded px-1 py-2 hover:bg-stone-50">
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={() => toggle(team.team_id)}
                    />
                    <span className="flex-1">{team.name}</span>
                    <span className="text-[11px] text-stone-500">
                      {team.rank ? `#${team.rank}` : ""} {team.record}
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        </aside>

        <section className="space-y-6">
          <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
            <div className="mb-2 flex items-baseline justify-between">
              <h2 className="text-lg text-stone-900">
                {metric === "power" ? "Power rating by week" : "Rank by week"}
              </h2>
              <p className="text-xs text-stone-500">
                {selected.length} team{selected.length === 1 ? "" : "s"}
              </p>
            </div>
            <div className="h-[380px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartRows} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
                  <CartesianGrid stroke="#e7e5e4" strokeDasharray="3 3" />
                  <XAxis dataKey="week" tick={{ fill: "#57534e", fontSize: 12 }} />
                  <YAxis
                    reversed={yReverse}
                    domain={yReverse ? [1, "dataMax"] : ["auto", "auto"]}
                    tick={{ fill: "#57534e", fontSize: 12 }}
                    width={48}
                  />
                  <Tooltip
                    contentStyle={{ borderRadius: 8, borderColor: "#d6d3d1" }}
                    formatter={(value: number, name: string) => {
                      const series = compare?.series.find((s) => s.team_id === name);
                      return [value, series?.name ?? name];
                    }}
                  />
                  <Legend
                    formatter={(value: string) =>
                      compare?.series.find((s) => s.team_id === value)?.name ?? value
                    }
                  />
                  {compare?.series.map((series, i) => (
                    <Line
                      key={series.team_id}
                      type="monotone"
                      dataKey={series.team_id}
                      stroke={COLORS[i % COLORS.length]}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <BoardSwitcher view={view} onView={setView} />
            {view === "statewide" ? (
              <div className="flex rounded-md bg-stone-100 p-0.5 text-xs">
                {[
                  { id: "", label: "All" },
                  { id: "DI", label: "DI" },
                  { id: "DII", label: "DII" },
                ].map((opt) => (
                  <button
                    key={opt.label}
                    type="button"
                    className={`rounded px-2 py-1 ${classFilter === opt.id ? "bg-white shadow-sm" : ""}`}
                    onClick={() => setClassFilter(opt.id)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          <RankingBoards
            view={view}
            onView={setView}
            statewide={statewideRows}
            districts={districts}
            regions={regions}
            selected={selected}
            onToggle={toggle}
            onCompare={selectIds}
            districtSort={districtSort}
            onDistrictSort={setDistrictSort}
            filterQuery={query}
            focusBoardId={focusBoardId}
          />
          <BoardTools teams={teams} onSeasonChanged={() => refresh()} />
        </section>
      </main>
    </div>
  );
}
