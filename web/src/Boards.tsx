import type { Board, RankRow } from "./api";

const REGION_LABELS: Record<string, string> = {
  "west-texas": "West Texas",
  "trans-pecos": "Trans-Pecos",
  "rolling-plains": "Rolling Plains",
  panhandle: "Panhandle / South Plains",
  "north-central": "North Central",
  "central-east-south": "Central / East / South",
};

function prettyRegion(raw: string) {
  return REGION_LABELS[raw] ?? raw.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export type BoardView = "statewide" | "districts" | "regions";

function formatDelta(delta: number | null) {
  if (delta == null || delta === 0) return "—";
  return delta > 0 ? `+${delta}` : String(delta);
}

type TableProps = {
  rows: RankRow[];
  selected: string[];
  onToggle: (id: string) => void;
  showDistrictWl?: boolean;
  showRegion?: boolean;
  showStatewide?: boolean;
  empty: string;
};

function RankTable({
  rows,
  selected,
  onToggle,
  showDistrictWl,
  showRegion,
  showStatewide,
  empty,
}: TableProps) {
  if (!rows.length) {
    return <p className="px-3 py-6 text-sm text-stone-500">{empty}</p>;
  }
  return (
    <div className="max-h-[70vh] overflow-auto">
      <table className="w-full text-left text-sm">
        <thead className="bg-stone-100 text-xs uppercase tracking-wide text-stone-500">
          <tr>
            <th className="px-3 py-2">Rk</th>
            <th className="px-3 py-2">Mv</th>
            <th className="px-3 py-2">Team</th>
            <th className="px-3 py-2">Rec</th>
            {showDistrictWl ? <th className="px-3 py-2">Dist</th> : null}
            {showRegion ? <th className="px-3 py-2">Region</th> : null}
            {showStatewide ? <th className="px-3 py-2">St</th> : null}
            <th className="px-3 py-2">Cls</th>
            <th className="px-3 py-2 text-right">Power</th>
            <th className="px-3 py-2 text-right">Conf</th>
            <th className="px-3 py-2 text-right">SOS</th>
            <th className="px-3 py-2">Notes</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.team_id}
              className={`border-t border-stone-100 ${
                selected.includes(row.team_id) ? "bg-amber-50" : ""
              }`}
            >
              <td className="px-3 py-1.5">
                {row.rank}
                {row.low_confidence ? "*" : ""}
              </td>
              <td className="px-3 py-1.5">{formatDelta(row.rank_delta)}</td>
              <td className="px-3 py-1.5">
                <button
                  type="button"
                  className="underline-offset-2 hover:underline"
                  onClick={() => onToggle(row.team_id)}
                >
                  {row.name}
                </button>
              </td>
              <td className="px-3 py-1.5">{row.record}</td>
              {showDistrictWl ? (
                <td className="px-3 py-1.5">{row.district_record}</td>
              ) : null}
              {showRegion ? (
                <td className="px-3 py-1.5 text-xs text-stone-500">{prettyRegion(row.region)}</td>
              ) : null}
              {showStatewide ? (
                <td className="px-3 py-1.5 text-stone-500">
                  {row.statewide_rank != null ? `#${row.statewide_rank}` : "—"}
                </td>
              ) : null}
              <td className="px-3 py-1.5 text-xs text-stone-500">{row.classification}</td>
              <td className="px-3 py-1.5 text-right tabular-nums">{row.power.toFixed(1)}</td>
              <td className="px-3 py-1.5 text-right tabular-nums text-stone-600">
                {row.confidence != null ? row.confidence.toFixed(2) : "—"}
                {row.low_confidence ? "*" : ""}
              </td>
              <td className="px-3 py-1.5 text-right tabular-nums text-stone-600">
                {row.sos != null ? row.sos.toFixed(2) : "—"}
                {row.density != null ? (
                  <span className="block text-[10px] text-stone-400">d {row.density.toFixed(2)}</span>
                ) : null}
              </td>
              <td className="max-w-[12rem] px-3 py-1.5 text-xs text-stone-500">{row.notes || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type Props = {
  view: BoardView;
  onView: (view: BoardView) => void;
  statewide: RankRow[];
  districts: Board[];
  regions: Board[];
  selected: string[];
  onToggle: (id: string) => void;
  onCompare: (ids: string[]) => void;
  districtSort: "power" | "standings";
  onDistrictSort: (sort: "power" | "standings") => void;
  filterQuery?: string;
  focusBoardId?: string;
};

function matchesQuery(row: RankRow, query: string) {
  if (!query.trim()) return true;
  const blob = `${row.name} ${row.team_id} ${row.district} ${row.region} ${row.classification}`.toLowerCase();
  return blob.includes(query.trim().toLowerCase());
}

export function BoardSwitcher({ view, onView }: Pick<Props, "view" | "onView">) {
  const tabs: { id: BoardView; label: string }[] = [
    { id: "statewide", label: "Statewide" },
    { id: "districts", label: "Districts" },
    { id: "regions", label: "Regions" },
  ];
  return (
    <div className="flex rounded-md bg-stone-100 p-0.5 text-sm">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={`rounded px-3 py-1 ${view === tab.id ? "bg-white shadow-sm" : ""}`}
          onClick={() => onView(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function RankingBoards({
  view,
  statewide,
  districts,
  regions,
  selected,
  onToggle,
  onCompare,
  districtSort,
  onDistrictSort,
  filterQuery = "",
  focusBoardId,
}: Props) {
  if (view === "statewide") {
    const filtered = statewide.filter((row) => matchesQuery(row, filterQuery));
    return (
      <div className="overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm">
        <p className="border-b border-stone-100 px-3 py-2 text-xs text-stone-500">
          {statewide.length} UIL six-man team{statewide.length === 1 ? "" : "s"} · ranks 1
          {statewide.length ? `–${statewide.length}` : ""} · scroll for the full field
          {filterQuery.trim()
            ? ` · showing ${filtered.length} match${filtered.length === 1 ? "" : "es"} for “${filterQuery.trim()}”`
            : ""}
        </p>
        <RankTable
          rows={filtered}
          selected={selected}
          onToggle={onToggle}
          showDistrictWl
          showRegion
          empty={
            filterQuery.trim()
              ? `No team matches “${filterQuery.trim()}”.`
              : "No rankings yet — waiting on the first final."
          }
        />
      </div>
    );
  }

  const allBoards = view === "districts" ? districts : regions;
  const focused = focusBoardId
    ? allBoards.filter((board) => board.id === focusBoardId)
    : [];
  const boards = focused.length ? focused : allBoards;
  if (!boards.length) {
    return (
      <div className="rounded-xl border border-stone-200 bg-white p-6 text-sm text-stone-500 shadow-sm">
        {view === "districts"
          ? "No district assignments on the current roster."
          : "No region assignments on the current roster."}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {view === "districts" ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-stone-500">
            Local power rank inside each district. Dist is district W-L — it does not
            feed the power formula.
          </p>
          <div className="flex rounded-md bg-stone-100 p-0.5 text-xs">
            <button
              type="button"
              className={`rounded px-2 py-1 ${districtSort === "power" ? "bg-white shadow-sm" : ""}`}
              onClick={() => onDistrictSort("power")}
            >
              Power
            </button>
            <button
              type="button"
              className={`rounded px-2 py-1 ${districtSort === "standings" ? "bg-white shadow-sm" : ""}`}
              onClick={() => onDistrictSort("standings")}
            >
              District W-L
            </button>
          </div>
        </div>
      ) : (
        <p className="text-xs text-stone-500">
          Local power rank inside each region. St is the statewide rank.
        </p>
      )}
      {focused.length ? (
        <p className="text-xs text-stone-600">
          Showing {focused[0].label}. Clear the compare chip to see every{" "}
          {view === "districts" ? "district" : "region"}.
        </p>
      ) : null}
      <div className="grid gap-4 xl:grid-cols-2">
        {boards.map((board) => {
          const rows =
            view === "districts" && districtSort === "standings" && board.standings
              ? board.standings
              : board.power;
          return (
            <section
              key={`${board.kind}:${board.id}`}
              className={`overflow-hidden rounded-xl border bg-white shadow-sm ${
                focusBoardId === board.id
                  ? "border-stone-900 ring-2 ring-stone-900/15"
                  : "border-stone-200"
              }`}
            >
              <header className="flex items-center justify-between gap-2 border-b border-stone-100 px-3 py-2">
                <div>
                  <h3 className="text-sm font-semibold text-stone-900">{board.label}</h3>
                  <p className="text-[11px] text-stone-500">
                    {board.team_ids.length} team{board.team_ids.length === 1 ? "" : "s"}
                  </p>
                </div>
                <button
                  type="button"
                  className="min-h-9 touch-manipulation rounded-full border border-stone-300 px-3 py-2 text-xs text-stone-700 hover:bg-stone-50"
                  onClick={() => onCompare(board.team_ids)}
                >
                  Compare on chart
                </button>
              </header>
              <RankTable
                rows={rows}
                selected={selected}
                onToggle={onToggle}
                showDistrictWl={view === "districts"}
                showStatewide
                empty="No teams in this group."
              />
            </section>
          );
        })}
      </div>
    </div>
  );
}
