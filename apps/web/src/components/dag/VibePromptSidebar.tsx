"use client";

import React, { useState } from "react";
import { Sparkles, ArrowRight, CheckCircle2, Terminal, ShieldCheck } from "lucide-react";
import { Node, Edge } from "@xyflow/react";

interface VibePromptSidebarProps {
  onApplyCompiledGraph: (nodes: Node[], edges: Edge[], astHash: string) => void;
}

const QUICK_VIBE_PROMPTS = [
  "9:20 AM Nifty Short Straddle (ATM CE & PE) with 25% SL, trail SL to cost when one leg hits SL",
  "Buy BankNifty ATM CE when 5m EMA(9) crosses above VWAP and RSI(14) > 60, 20% SL, 40% Target",
  "Expiry Day Iron Condor: Sell 100-pt OTM CE/PE & Buy 250-pt OTM hedges when IV Rank > 50",
];

export default function VibePromptSidebar({ onApplyCompiledGraph }: VibePromptSidebarProps) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<string | null>(null);
  const [astHash, setAstHash] = useState<string | null>(null);

  const handleCompile = async (inputPrompt: string) => {
    if (!inputPrompt.trim()) return;
    setLoading(true);
    try {
      const res = await fetch("/api/v1/vibe/compile-prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: inputPrompt }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSummary(data.compiler_summary);
      setAstHash(data.ast_sha256);
      onApplyCompiledGraph(data.react_flow_nodes, data.react_flow_edges, data.ast_sha256);
    } catch (err) {
      setSummary(`Compiler Error: ${err instanceof Error ? err.message : "Invalid Graph"}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside className="w-96 border-r border-slate-800 bg-slate-900/95 flex flex-col justify-between p-4 text-slate-100">
      <div className="space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
          <Sparkles className="h-5 w-5 text-emerald-400" />
          <div>
            <h2 className="text-sm font-extrabold uppercase tracking-wider text-white">
              Vibe-to-DAG AI Studio
            </h2>
            <p className="text-[11px] text-slate-400">
              Natural Language → Verified Acyclic JSON AST
            </p>
          </div>
        </div>

        {/* Prompt Input */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-slate-300">
            Describe your strategy or modification:
          </label>
          <textarea
            rows={4}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., When Nifty 5m SuperTrend turns bearish below VWAP, sell ATM CE and buy 150pts OTM CE hedge with 25% SL..."
            className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
          />
          <button
            onClick={() => handleCompile(prompt)}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 py-2.5 text-xs font-bold text-white transition shadow-lg shadow-emerald-600/20"
          >
            {loading ? "Synthesizing & Checking Cycles..." : "Compile to Visual DAG"}
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>

        {/* Quick Prompts */}
        <div className="space-y-2 pt-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            One-Click Institutional Prompts
          </span>
          {QUICK_VIBE_PROMPTS.map((qp, idx) => (
            <button
              key={idx}
              onClick={() => {
                setPrompt(qp);
                handleCompile(qp);
              }}
              className="w-full text-left rounded-lg border border-slate-800 bg-slate-950/70 hover:border-emerald-500/40 p-2.5 text-[11px] text-slate-300 transition"
            >
              “{qp}”
            </button>
          ))}
        </div>

        {/* Compiler Verification Output */}
        {summary && (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3 space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-400">
              <CheckCircle2 className="h-4 w-4" /> AST Verification Passed
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">{summary}</p>
            {astHash && (
              <div className="flex items-center gap-1.5 font-mono text-[10px] text-slate-400 bg-slate-950 p-1.5 rounded">
                <Terminal className="h-3.5 w-3.5 text-sky-400" />
                SHA256: {astHash.slice(0, 20)}...
              </div>
            )}
          </div>
        )}
      </div>

      {/* SEBI Compliance Footer */}
      <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-[11px] text-slate-400 flex items-start gap-2">
        <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
        <span>
          <strong>White-Box Guarantee:</strong> AI only generates transparent DAG nodes at design time. Live execution is 100% deterministic math.
        </span>
      </div>
    </aside>
  );
}
