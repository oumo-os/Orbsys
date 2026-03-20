"use client";

import { useEffect, useState } from "react";
import { competenceApi } from "@/lib/api";
import { TrendingUp } from "lucide-react";

interface CompetenceScore {
  dormain_id: string;
  dormain_name: string;
  w_s: number;
  w_s_peak: number;
  w_h: number;
  volatility_k: number;
  proof_count: number;
  last_activity_at: string | null;
  mcmp_status: string;
}

interface ScoresResponse {
  member_id: string;
  scores: CompetenceScore[];
}

function ScoreBar({ value, peak }: { value: number; peak: number }) {
  const max = Math.max(peak, 120);
  const pctValue = (value / max) * 100;
  const pctPeak = (peak / max) * 100;
  return (
    <div className="relative h-1.5 bg-orbsys-surface rounded-full overflow-hidden">
      {/* Peak marker */}
      <div
        className="absolute h-full bg-orbsys-gold/20 rounded-full"
        style={{ width: `${pctPeak}%` }}
      />
      {/* Current */}
      <div
        className="absolute h-full bg-orbsys-gold rounded-full transition-all"
        style={{ width: `${pctValue}%` }}
      />
    </div>
  );
}

const MCMP_COLOURS: Record<string, string> = {
  active:  "text-emerald-400",
  decayed: "text-yellow-400",
  dormant: "text-zinc-500",
};

export default function CompetencePage() {
  const [data, setData] = useState<ScoresResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    competenceApi.myScores()
      .then((r) => setData(r.data))
      .catch(() => setError("Failed to load competence scores"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-lg text-orbsys-text">Competence</h1>
        <p className="text-xs text-orbsys-muted font-mono mt-0.5">
          Your W_s scores across Dormains
        </p>
      </div>

      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="h-3 bg-orbsys-surface rounded w-1/3 mb-3" />
              <div className="h-1.5 bg-orbsys-surface rounded" />
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="text-xs font-mono text-red-400 bg-red-950/30 border border-red-800/40 rounded px-4 py-3">
          {error}
        </div>
      )}

      {data && data.scores.length === 0 && (
        <div className="card p-8 text-center">
          <p className="text-sm font-mono text-orbsys-muted">
            No competence scores yet. Contribute to Commons threads and
            participate in Cell deliberations to earn W_s.
          </p>
        </div>
      )}

      {data && data.scores.length > 0 && (
        <div className="space-y-3">
          {data.scores.map((score) => (
            <div key={score.dormain_id} className="card p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-sm font-medium text-orbsys-text">
                    {score.dormain_name}
                  </h3>
                  <p
                    className={`text-[10px] font-mono capitalize mt-0.5 ${
                      MCMP_COLOURS[score.mcmp_status] ?? "text-orbsys-muted"
                    }`}
                  >
                    {score.mcmp_status}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-mono text-lg font-bold text-orbsys-gold leading-none">
                    {score.w_s.toFixed(1)}
                  </p>
                  <p className="text-[10px] font-mono text-orbsys-muted">
                    W_s
                  </p>
                </div>
              </div>

              <ScoreBar value={score.w_s} peak={score.w_s_peak} />

              <div className="flex items-center gap-4 mt-3 text-[10px] font-mono text-orbsys-muted">
                <span>Peak {score.w_s_peak.toFixed(1)}</span>
                <span>W_h {score.w_h.toFixed(1)}</span>
                <span>K = {score.volatility_k}</span>
                <span>{score.proof_count} proof{score.proof_count !== 1 ? "s" : ""}</span>
                {score.last_activity_at && (
                  <span>
                    Last activity{" "}
                    {new Date(score.last_activity_at).toLocaleDateString("en-GB", {
                      day: "numeric", month: "short",
                    })}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* W_h claims link */}
      <div className="card p-4 border-orbsys-gold/20">
        <div className="flex items-center gap-2 text-xs font-mono">
          <TrendingUp size={12} className="text-orbsys-gold" />
          <span className="text-orbsys-muted">
            Have professional credentials?
          </span>
          <button
            className="text-orbsys-gold hover:underline"
            onClick={() => alert("W_h claim form — coming soon")}
          >
            Submit a W_h claim →
          </button>
        </div>
      </div>
    </div>
  );
}
