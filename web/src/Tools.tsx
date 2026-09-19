import { useEffect, useState } from "react";
import { api, type Team, type WhatIfResponse } from "./api";

type Props = {
  teams: Team[];
  onSeasonChanged: () => Promise<void>;
};

export function BoardTools({ teams, onSeasonChanged }: Props) {
  const [homeId, setHomeId] = useState("");
  const [awayId, setAwayId] = useState("");
  const [homeScore, setHomeScore] = useState("54");
  const [awayScore, setAwayScore] = useState("36");
  const [neutral, setNeutral] = useState(false);
  const [districtGame, setDistrictGame] = useState(false);
  const [whatIf, setWhatIf] = useState<WhatIfResponse | null>(null);
  const [whatIfError, setWhatIfError] = useState<string | null>(null);
  const [whatIfBusy, setWhatIfBusy] = useState(false);

  const [ingestHome, setIngestHome] = useState("");
  const [ingestAway, setIngestAway] = useState("");
  const [ingestHomeScore, setIngestHomeScore] = useState("");
  const [ingestAwayScore, setIngestAwayScore] = useState("");
  const [ingestWeek, setIngestWeek] = useState("5");
  const [ingestJson, setIngestJson] = useState("");
  const [ingestMsg, setIngestMsg] = useState<string | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);
  const [ingestBusy, setIngestBusy] = useState(false);

  useEffect(() => {
    if (!teams.length) return;
    setHomeId((cur) => cur || teams[0].team_id);
    setAwayId((cur) => cur || teams[1]?.team_id || teams[0].team_id);
  }, [teams]);

  async function runWhatIf() {
    setWhatIfBusy(true);
    setWhatIfError(null);
    try {
      const report = await api.whatIf({
        home_id: homeId,
        away_id: awayId,
        home_score: Number(homeScore),
        away_score: Number(awayScore),
        neutral,
        district_game: districtGame,
      });
      setWhatIf(report);
    } catch (err) {
      setWhatIf(null);
      setWhatIfError(err instanceof Error ? err.message : String(err));
    } finally {
      setWhatIfBusy(false);
    }
  }

  async function runIngest() {
    setIngestBusy(true);
    setIngestError(null);
    setIngestMsg(null);
    try {
      let payload: unknown;
      if (ingestJson.trim()) {
        payload = JSON.parse(ingestJson);
      } else {
        if (!ingestHome || !ingestAway || ingestHomeScore === "" || ingestAwayScore === "") {
          throw new Error("Enter both teams and scores, or paste a JSON feed.");
        }
        payload = {
          games: [
            {
              week: Number(ingestWeek) || 1,
              home: ingestHome,
              away: ingestAway,
              home_score: Number(ingestHomeScore),
              away_score: Number(ingestAwayScore),
              status: "final",
            },
          ],
        };
      }
      const result = await api.ingest(payload);
      setIngestMsg(`Merged ${result.updates} update${result.updates === 1 ? "" : "s"} into the live season.`);
      await onSeasonChanged();
    } catch (err) {
      setIngestError(err instanceof Error ? err.message : String(err));
    } finally {
      setIngestBusy(false);
    }
  }

  const options = teams.map((team) => (
    <option key={team.team_id} value={team.team_id}>
      {team.name}
    </option>
  ));

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-stone-900">What-if</h2>
        <p className="mt-1 text-xs text-stone-500">
          Provisional Friday. Does not write back to the season. Same engine as{" "}
          <code className="rounded bg-stone-100 px-1">sixman-rank what-if</code>.
        </p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          <label className="text-xs text-stone-500">
            Home
            <select
              className="mt-1 w-full rounded-md border border-stone-300 px-2 py-1.5 text-sm text-stone-900"
              value={homeId}
              onChange={(e) => setHomeId(e.target.value)}
            >
              {options}
            </select>
          </label>
          <label className="text-xs text-stone-500">
            Away
            <select
              className="mt-1 w-full rounded-md border border-stone-300 px-2 py-1.5 text-sm text-stone-900"
              value={awayId}
              onChange={(e) => setAwayId(e.target.value)}
            >
              {options}
            </select>
          </label>
          <label className="text-xs text-stone-500">
            Home score
            <input
              className="mt-1 w-full rounded-md border border-stone-300 px-2 py-1.5 text-sm"
              value={homeScore}
              onChange={(e) => setHomeScore(e.target.value)}
              inputMode="numeric"
            />
          </label>
          <label className="text-xs text-stone-500">
            Away score
            <input
              className="mt-1 w-full rounded-md border border-stone-300 px-2 py-1.5 text-sm"
              value={awayScore}
              onChange={(e) => setAwayScore(e.target.value)}
              inputMode="numeric"
            />
          </label>
        </div>
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-stone-600">
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={neutral} onChange={(e) => setNeutral(e.target.checked)} />
            Neutral site
          </label>
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={districtGame}
              onChange={(e) => setDistrictGame(e.target.checked)}
            />
            District game
          </label>
        </div>
        <button
          type="button"
          className="mt-3 rounded-md bg-stone-900 px-3 py-1.5 text-sm text-white disabled:opacity-60"
          disabled={whatIfBusy || !homeId || !awayId}
          onClick={() => void runWhatIf()}
        >
          {whatIfBusy ? "Simulating…" : "Run what-if"}
        </button>
        {whatIfError ? <p className="mt-2 text-sm text-red-700">{whatIfError}</p> : null}
        {whatIf ? (
          <div className="mt-3 overflow-x-auto">
            <p className="text-xs text-stone-500">
              {whatIf.game.home_id} {whatIf.game.home_score}–{whatIf.game.away_score}{" "}
              {whatIf.game.away_id} · week {whatIf.through_week}
              {whatIf.game.neutral ? " · neutral" : ""}
            </p>
            {whatIf.movers.length ? (
              <table className="mt-2 w-full text-left text-xs">
                <thead className="text-stone-500">
                  <tr>
                    <th className="py-1">Team</th>
                    <th className="py-1">Rk</th>
                    <th className="py-1">New</th>
                    <th className="py-1 text-right">Power</th>
                    <th className="py-1 text-right">ΔP</th>
                  </tr>
                </thead>
                <tbody>
                  {whatIf.movers.map((row) => (
                    <tr key={row.team_id} className="border-t border-stone-100">
                      <td className="py-1">{row.name}</td>
                      <td className="py-1">{row.rank_before ?? "—"}</td>
                      <td className="py-1">
                        {row.rank_after}
                        {row.rank_delta ? ` (${row.rank_delta > 0 ? "+" : ""}${row.rank_delta})` : ""}
                      </td>
                      <td className="py-1 text-right tabular-nums">
                        {row.power_before ?? "—"} → {row.power_after.toFixed(1)}
                      </td>
                      <td className="py-1 text-right tabular-nums">
                        {row.power_delta > 0 ? "+" : ""}
                        {row.power_delta.toFixed(1)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="mt-2 text-sm text-stone-500">No rank movement from that score.</p>
            )}
          </div>
        ) : null}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-stone-900">Ingest a final</h2>
        <p className="mt-1 text-xs text-stone-500">
          Same payload as <code className="rounded bg-stone-100 px-1">POST /api/ingest</code> /{" "}
          <code className="rounded bg-stone-100 px-1">SIXMAN_FEED_URL</code>. Writes into the live
          season on the computer running <code className="rounded bg-stone-100 px-1">sixman-rank serve</code>.
        </p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          <label className="text-xs text-stone-500">
            Week
            <input
              className="mt-1 w-full rounded-md border border-stone-300 px-2 py-1.5 text-sm"
              value={ingestWeek}
              onChange={(e) => setIngestWeek(e.target.value)}
              inputMode="numeric"
            />
          </label>
          <span />
          <label className="text-xs text-stone-500">
            Home (name or slug)
            <input
              className="mt-1 w-full rounded-md border border-stone-300 px-2 py-1.5 text-sm"
              value={ingestHome}
              onChange={(e) => setIngestHome(e.target.value)}
              placeholder="Borden County"
            />
          </label>
          <label className="text-xs text-stone-500">
            Away
            <input
              className="mt-1 w-full rounded-md border border-stone-300 px-2 py-1.5 text-sm"
              value={ingestAway}
              onChange={(e) => setIngestAway(e.target.value)}
              placeholder="Garden City"
            />
          </label>
          <label className="text-xs text-stone-500">
            Home score
            <input
              className="mt-1 w-full rounded-md border border-stone-300 px-2 py-1.5 text-sm"
              value={ingestHomeScore}
              onChange={(e) => setIngestHomeScore(e.target.value)}
              inputMode="numeric"
            />
          </label>
          <label className="text-xs text-stone-500">
            Away score
            <input
              className="mt-1 w-full rounded-md border border-stone-300 px-2 py-1.5 text-sm"
              value={ingestAwayScore}
              onChange={(e) => setIngestAwayScore(e.target.value)}
              inputMode="numeric"
            />
          </label>
        </div>
        <label className="mt-2 block text-xs text-stone-500">
          Or paste a feed JSON
          <textarea
            className="mt-1 h-20 w-full rounded-md border border-stone-300 px-2 py-1.5 font-mono text-xs"
            value={ingestJson}
            onChange={(e) => setIngestJson(e.target.value)}
            placeholder='{"games":[{"week":5,"home":"Borden County","away":"Garden City","home_score":54,"away_score":36,"status":"final"}]}'
          />
        </label>
        <button
          type="button"
          className="mt-3 rounded-md bg-stone-900 px-3 py-1.5 text-sm text-white disabled:opacity-60"
          disabled={ingestBusy}
          onClick={() => void runIngest()}
        >
          {ingestBusy ? "Posting…" : "Post to live season"}
        </button>
        {ingestError ? <p className="mt-2 text-sm text-red-700">{ingestError}</p> : null}
        {ingestMsg ? <p className="mt-2 text-sm text-emerald-800">{ingestMsg}</p> : null}
      </section>
    </div>
  );
}
