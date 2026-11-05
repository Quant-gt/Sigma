"use client";

import React, { useState } from "react";
import { Flame, ShieldAlert, TrendingUp, TrendingDown, Scale, ArrowUpRight } from "lucide-react";

const SAMPLE_VERDICT = {
  underlying: "NIFTY 50 (Lot Size: 65)",
  timestamp_ist: "08:45:00 IST Pre-Market Committee",
  regime_classification: "LOW_VOL_THETA_DECAY",
  bull_probability_pct: 28,
  bear_probability_pct: 22,
  neutral_probability_pct: 50,
  recommended_lot_multiplier_scale: 1.0,
  recommended_whitebox_blueprints: [
    "WB-01: 09:20 Rolling Short Straddle (SL-to-Cost)",
    "WB-03: Iron Butterfly Defined-Risk Decay",
  ],
  debate_transcript: [
    {
      speaker: "OPTIONS_FLOW_ANALYST",
      stance: "NEUTRAL_RANGE",
      headline: "PCR at 1.04 with Max Pain pinned at 24,400; India VIX compressed at 13.2 (-3.4%)",
      evidence_points: [
        "Put Wall firmly established at 24,200 PE (84L OI) vs Call Wall at 24,600 CE (91L OI).",
        "FII Index Futures Net Long steady at 52.4% — no aggressive directional unwinding.",
      ],
      conviction: 84,
    },
    {
      speaker: "BULL_RESEARCHER",
      stance: "BULLISH",
      headline: "Put writing at 24,350 & positive banking breadth favor dip-buying above VWAP",
      evidence_points: [
        "GIFT Nifty signals a +35 pt opening near 24,415.",
        "Sustaining above 24,450 for two 5m candles forces gamma covering on 24,400 CE writers.",
      ],
      conviction: 68,
    },
    {
      speaker: "BEAR_RESEARCHER",
      stance: "BEARISH",
      headline: "Heavy 24,500–24,600 Call supply + declining intraday ATR favors fade at resistance",
      evidence_points: [
        "Last 4 sessions saw morning gap-ups fade back toward daily VWAP by 11:30 AM.",
        "Option buyers face severe theta headwind unless VIX expands above 14.8.",
      ],
      conviction: 74,
    },
    {
      speaker: "CHIEF_RISK_OFFICER",
      stance: "RISK_ALERT",
      headline: "Verdict: Rangebound Theta Regime — Approve Non-Directional Short Vega Blueprints",
      evidence_points: [
        "Approved Lot Scaling: 1.0x (100% normal allocation).",
        "Hard Stop-Loss capped at 25% per leg with automatic Move-SL-to-Cost enabled.",
      ],
      conviction: 94,
    },
  ],
};

export default function PreMarketWarRoom() {
  const [verdict] = useState(SAMPLE_VERDICT);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 text-slate-100 shadow-2xl space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-amber-500/10 p-2.5 border border-amber-500/30">
            <Flame className="h-6 w-6 text-amber-400" />
          </div>
          <div>
            <h2 className="text-lg font-extrabold text-white">
              TradingAgents Pre-Market War Room ({verdict.underlying})
            </h2>
            <p className="text-xs text-slate-400">{verdict.timestamp_ist}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="rounded-lg bg-emerald-500/15 border border-emerald-500/30 px-3 py-1.5 text-xs font-bold text-emerald-300">
            Regime: {verdict.regime_classification}
          </span>
          <span className="rounded-lg bg-sky-500/15 border border-sky-500/30 px-3 py-1.5 text-xs font-mono font-bold text-sky-300">
            CRO Lot Scale: {verdict.recommended_lot_multiplier_scale * 100}%
          </span>
        </div>
      </div>

      {/* Probability Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs font-bold">
          <span className="text-emerald-400">BULL CASE ({verdict.bull_probability_pct}%)</span>
          <span className="text-amber-300">RANGE / THETA ({verdict.neutral_probability_pct}%)</span>
          <span className="text-rose-400">BEAR CASE ({verdict.bear_probability_pct}%)</span>
        </div>
        <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-950 border border-slate-800">
          <div style={{ width: `${verdict.bull_probability_pct}%` }} className="bg-emerald-500" />
          <div style={{ width: `${verdict.neutral_probability_pct}%` }} className="bg-amber-500" />
          <div style={{ width: `${verdict.bear_probability_pct}%` }} className="bg-rose-500" />
        </div>
      </div>

      {/* Multi-Agent Debate Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {verdict.debate_transcript.map((turn, idx) => {
          const isBull = turn.speaker === "BULL_RESEARCHER";
          const isBear = turn.speaker === "BEAR_RESEARCHER";
          const isCro = turn.speaker === "CHIEF_RISK_OFFICER";

          return (
            <div
              key={idx}
              className={`rounded-xl border p-4 space-y-2.5 ${
                isBull
                  ? "border-emerald-500/30 bg-emerald-950/10"
                  : isBear
                  ? "border-rose-500/30 bg-rose-950/10"
                  : isCro
                  ? "border-amber-500/40 bg-amber-950/15"
                  : "border-slate-800 bg-slate-950/80"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wider">
                  {isBull && <TrendingUp className="h-4 w-4 text-emerald-400" />}
                  {isBear && <TrendingDown className="h-4 w-4 text-rose-400" />}
                  {isCro && <ShieldAlert className="h-4 w-4 text-amber-400" />}
                  {!isBull && !isBear && !isCro && <Scale className="h-4 w-4 text-sky-400" />}
                  {turn.speaker.replace(/_/g, " ")}
                </span>
                <span className="font-mono text-[11px] text-slate-400">
                  Conviction: <strong className="text-white">{turn.conviction}/100</strong>
                </span>
              </div>

              <p className="text-xs font-bold text-white">{turn.headline}</p>
              <ul className="space-y-1 text-xs text-slate-300 list-disc list-inside">
                {turn.evidence_points.map((pt, i) => (
                  <li key={i}>{pt}</li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      {/* Recommended Blueprints Footer */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-slate-950 p-4 border border-slate-800">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
            CRO-Matched White-Box Blueprints for Today’s Regime
          </span>
          <div className="flex flex-wrap gap-2 mt-1.5">
            {verdict.recommended_whitebox_blueprints.map((bp, i) => (
              <span
                key={i}
                className="flex items-center gap-1 rounded-lg bg-slate-900 border border-slate-700 px-3 py-1 text-xs font-semibold text-emerald-300"
              >
                {bp} <ArrowUpRight className="h-3.5 w-3.5" />
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
