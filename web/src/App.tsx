import { useCallback, useEffect, useMemo, useState } from "react";
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
  setStoredApiBase,
  type Board,
  type CompareResponse,
  type RankRow,
  type Status,
  type Team,
} from "./api";
import { BoardSwitcher, RankingBoards, type BoardView } from "./Boards";
import { COLORS } from "./lib/utils";

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
  panhandle: "Panhandle",
};

function prettyPlace(raw: string) {
  return REGION_LABELS[raw] ?? raw.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
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
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [apiBaseDraft, setApiBaseDraft] = useState(getStoredApiBase);

  const refresh = useCallback(async (ids?: string[]) => {
    const [st, teamPayload, presetPayload, rankPayload, boardPayload] = await Promise.all([
      api.status(),
      api.teams(),
      api.presets(),
      api.rankings(),
      api.boards(),
    ]);
    setStatus(st);
    setTeams(teamPayload.teams);
    setPresets(presetPayload.presets);
    setRows(rankPayload.rankings);
    setDistricts(boardPayload.districts);
    setRegions(boardPayload.regions);
    const nextIds =
      ids ??
      (selected.length
        ? selected
        : presetPayload.presets.last_week_top10?.length
          ? presetPayload.presets.last_week_top10
          : presetPayload.presets.this_week_top10);
    if (ids || selected.length === 0) {
      setSelected(nextIds);
    }
    const series = await api.compare(nextIds, metric);
    setCompare(series);
  }, [metric, selected.length]);

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selected.length) return;
    api.compare(selected, metric).then(setCompare).catch((err: Error) => setError(err.message));
  }, [selected, metric]);

  useEffect(() => {
    const ms = Math.max(8, status?.interval_sec ?? 20) * 1000;
    const timer = window.setInterval(() => {
      refresh(selected).catch(() => undefined);
    }, ms);
    return () => window.clearInterval(timer);
  }, [refresh, selected, status?.interval_sec]);

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

  const filteredTeams = teams.filter((team) => {
    const blob = `${team.name} ${team.district} ${team.region} ${team.classification}`.toLowerCase();
    return blob.includes(query.toLowerCase());
  });

  const namedPresets = Object.entries(presets).filter(
    ([key]) => !key.startsWith("district:") && !key.startsWith("region:"),
  );
  const districtPresets = Object.entries(presets).filter(([key]) => key.startsWith("district:"));
  const regionPresets = Object.entries(presets).filter(([key]) => key.startsWith("region:"));

  async function onSync() {
    setSyncing(true);
    try {
      await api.sync();
      await refresh(selected);
    } finally {
      setSyncing(false);
    }
  }

  function toggle(id: string) {
    setSelected((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  }

  const yReverse = metric === "rank";

  return (
    <div className="min-h-screen px-4 py-6 md:px-8">
      <header className="mx-auto flex max-w-7xl flex-col gap-3 border-b border-stone-300 pb-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-stone-500">Texas UIL Six-Man</p>
          <h1 className="font-sans text-3xl tracking-tight text-stone-900 md:text-4xl">
            Live power rankings
          </h1>
          <p className="mt-1 max-w-xl text-sm text-stone-600">
            Scores are pulled on Thursday, Friday, and Saturday. The model republishes as
            finals land — pick any clubs, or load last week&apos;s Top 10.
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
          <h2 className="font-semibold text-stone-900">Install on a phone</h2>
          <p className="mt-1 text-stone-600">
            This is a web app. The Android APK wraps the same GUI and ships a bundled
            season. Chrome can also install it from the menu as an app.
          </p>
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
            On the same Wi-Fi as your computer, run{" "}
            <code className="rounded bg-stone-100 px-1">sixman-rank serve --host 0.0.0.0 --port 43127</code>
            {" "}and paste that machine&apos;s address. Leave blank for the snapshot inside the APK.
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
          <div className="mb-3 flex flex-wrap gap-1.5">
            {namedPresets.map(([key, ids]) => (
              <button
                key={key}
                type="button"
                onClick={() => setSelected(ids)}
                className="rounded-full border border-stone-300 px-2 py-0.5 text-[11px] text-stone-700 hover:bg-stone-50"
              >
                {PRESET_LABELS[key] ?? key}
              </button>
            ))}
            {districtPresets.map(([key, ids]) => (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setSelected(ids);
                  setView("districts");
                }}
                className="rounded-full border border-dashed border-stone-300 px-2 py-0.5 text-[11px] text-stone-600 hover:bg-stone-50"
              >
                {key.replace("district:", "")}
              </button>
            ))}
            {regionPresets.map(([key, ids]) => (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setSelected(ids);
                  setView("regions");
                }}
                className="rounded-full border border-dashed border-stone-400 px-2 py-0.5 text-[11px] text-stone-600 hover:bg-stone-50"
              >
                {prettyPlace(key.replace("region:", ""))}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setSelected([])}
              className="rounded-full px-2 py-0.5 text-[11px] text-stone-500 underline"
            >
              Clear
            </button>
          </div>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter teams…"
            className="mb-2 w-full rounded-md border border-stone-300 px-2 py-1.5 text-sm"
          />
          <ul className="max-h-[28rem] space-y-1 overflow-auto text-sm">
            {filteredTeams.map((team) => {
              const on = selected.includes(team.team_id);
              return (
                <li key={team.team_id}>
                  <label className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 hover:bg-stone-50">
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
          </div>
          <RankingBoards
            view={view}
            onView={setView}
            statewide={rows}
            districts={districts}
            regions={regions}
            selected={selected}
            onToggle={toggle}
            onCompare={setSelected}
            districtSort={districtSort}
            onDistrictSort={setDistrictSort}
          />
        </section>
      </main>
    </div>
  );
}
