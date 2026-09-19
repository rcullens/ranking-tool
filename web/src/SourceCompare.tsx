import { useMemo, useState } from "react";
import type { SourceKey, SourceRankRow, SourceRanksResponse } from "./api";

const SOURCES: { key: SourceKey; label: string }[] = [
  { key: "maxpreps", label: "MaxPreps" },
  { key: "smf", label: "SMF" },
  { key: "dctf", label: "DCTF" },
];

function fmtRank(value: number | null | undefined) {
  return value == null ? "NR" : String(value);
}

function fmtDelta(value: number | null | undefined) {
  if (value == null) return "—";
  if (value === 0) return "0";
  return value > 0 ? `+${value}` : String(value);
}

function deltaClass(value: number | null | undefined) {
  if (value == null) return "text-stone-400";
  if (value === 0) return "text-emerald-700";
  if (Math.abs(value) <= 2) return "text-emerald-800";
  if (Math.abs(value) >= 10) return "text-amber-800";
  return "text-stone-700";
}

type Props = {
  data: SourceRanksResponse | null;
  query?: string;
};

export function SourceCompare({ data, query = "" }: Props) {
  const [shown, setShown] = useState<Record<SourceKey, boolean>>({
    maxpreps: true,
    smf: true,
    dctf: true,
  });

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (data?.rows ?? []).filter((row) => {
      if (!q) return true;
      const blob = `${row.name} ${row.team_id} ${row.district} ${row.region} ${row.classification} ${row.association ?? ""}`.toLowerCase();
      return blob.includes(q);
    });
  }, [data, query]);

  function toggle(key: SourceKey) {
    setShown((cur) => ({ ...cur, [key]: !cur[key] }));
  }

  if (!data) {
    return (
      <div className="rounded-xl border border-stone-200 bg-white p-6 text-sm text-stone-500 shadow-sm">
        Loading public-board ranks…
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stone-100 px-3 py-2">
        <div>
          <h3 className="text-sm font-semibold text-stone-900">Compare sources</h3>
          <p className="text-[11px] text-stone-500">
            Our statewide power rank vs MaxPreps, SixManFootball, and DCTF. Δ = ours − theirs.
            NR / — means that board has not listed the team.
          </p>
        </div>
        <div className="flex flex-wrap gap-1">
          {SOURCES.map((src) => {
            const meta = data.sources[src.key];
            const on = shown[src.key];
            return (
              <button
                key={src.key}
                type="button"
                aria-pressed={on}
                onClick={() => toggle(src.key)}
                className={`min-h-9 touch-manipulation rounded-full border px-3 py-1.5 text-xs ${
                  on ? "border-stone-900 bg-stone-900 text-white" : "border-stone-300 bg-white text-stone-700"
                }`}
              >
                {src.label}
                {meta?.week && meta.week !== "—" ? ` · ${meta.week}` : ""}
              </button>
            );
          })}
        </div>
      </div>
      <p className="border-b border-stone-100 px-3 py-2 text-xs text-stone-500">
        {data.rows.length} teams · showing {rows.length}
        {query.trim() ? ` match${rows.length === 1 ? "" : "es"} for “${query.trim()}”` : ""}
        {data.pulled_at ? ` · pulled ${new Date(data.pulled_at).toLocaleString()}` : ""}
      </p>
      <div className="max-h-[70vh] overflow-auto">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 bg-stone-100 text-xs uppercase tracking-wide text-stone-500">
            <tr>
              <th className="px-3 py-2">Team</th>
              <th className="px-3 py-2 text-right">Our</th>
              {shown.maxpreps ? (
                <>
                  <th className="px-3 py-2 text-right">MaxPreps</th>
                  <th className="px-3 py-2 text-right">Δ MP</th>
                </>
              ) : null}
              {shown.smf ? (
                <>
                  <th className="px-3 py-2 text-right">SMF</th>
                  <th className="px-3 py-2 text-right">Δ SMF</th>
                </>
              ) : null}
              {shown.dctf ? (
                <>
                  <th className="px-3 py-2 text-right">DCTF</th>
                  <th className="px-3 py-2 text-right">Δ DCTF</th>
                </>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <CompareRow key={row.team_id} row={row} shown={shown} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CompareRow({
  row,
  shown,
}: {
  row: SourceRankRow;
  shown: Record<SourceKey, boolean>;
}) {
  const highlight = row.team_id === "aquilla" || row.team_id === "first-baptist-christian";
  return (
    <tr className={`border-t border-stone-100 ${highlight ? "bg-amber-50" : ""}`}>
      <td className="px-3 py-1.5">
        <div className="font-medium text-stone-900">{row.name}</div>
        <div className="text-[11px] text-stone-500">
          {row.association || "UIL"} · {row.classification}
        </div>
      </td>
      <td className="px-3 py-1.5 text-right tabular-nums">{fmtRank(row.our_rank)}</td>
      {shown.maxpreps ? (
        <>
          <td className="px-3 py-1.5 text-right tabular-nums">{fmtRank(row.maxpreps)}</td>
          <td className={`px-3 py-1.5 text-right tabular-nums ${deltaClass(row.delta_maxpreps)}`}>
            {fmtDelta(row.delta_maxpreps)}
          </td>
        </>
      ) : null}
      {shown.smf ? (
        <>
          <td className="px-3 py-1.5 text-right tabular-nums">{fmtRank(row.smf)}</td>
          <td className={`px-3 py-1.5 text-right tabular-nums ${deltaClass(row.delta_smf)}`}>
            {fmtDelta(row.delta_smf)}
          </td>
        </>
      ) : null}
      {shown.dctf ? (
        <>
          <td className="px-3 py-1.5 text-right tabular-nums">{fmtRank(row.dctf)}</td>
          <td className={`px-3 py-1.5 text-right tabular-nums ${deltaClass(row.delta_dctf)}`}>
            {fmtDelta(row.delta_dctf)}
          </td>
        </>
      ) : null}
    </tr>
  );
}
