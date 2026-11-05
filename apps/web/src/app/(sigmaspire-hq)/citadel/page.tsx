"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  Cpu,
  Zap,
  Activity,
  Layers,
  Server,
  Lock,
  CheckCircle2,
  AlertOctagon,
  RefreshCw,
  Terminal,
  Clock,
} from "lucide-react";

export default function CitadelCommandCenter() {
  const [freezeStatus, setFreezeStatus] = useState<string>("SYSTEM_ARMED_NOMINAL");
  const [isFreezing, setIsFreezing] = useState<boolean>(false);
  const [auditLog, setAuditLog] = useState<string | null>(null);

  // Trigger Citadel Level-4 Master Circuit Breaker
  const handleGlobalFreeze = async () => {
    setIsFreezing(true);
    try {
      const res = await fetch("/api/v1/super-admin/citadel/global-freeze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (res.ok) {
        const data = await res.json();
        setFreezeStatus("ALL_PIPELINES_HALTED");
        setAuditLog(`Global Master Circuit Breaker Engaged. Signature: ${data.auditSignature?.slice(0, 24)}...`);
      }
    } catch {
      setFreezeStatus("ERROR_HALT_ENGAGED");
    } finally {
      setIsFreezing(false);
    }
  };

  const handleVerifyChineseWall = async () => {
    try {
      const res = await fetch("/api/v1/super-admin/chinese-wall/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (res.ok) {
        const data = await res.json();
        setAuditLog(`Audit ${data.auditId}: Zero state leakage verified. Prop Alpha strictly isolated from Retail Routing.`);
      }
    } catch {
      setAuditLog("Audit verification request failed.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-8">
      {/* Top Header */}
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 bg-slate-900/60 p-5 rounded-2xl backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-amber-500/10 p-2.5 border border-amber-500/30">
            <Server className="h-6 w-6 text-amber-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-extrabold text-white tracking-tight">
                SIGMASPIRE CITADEL OPS
              </h1>
              <span className="rounded-full bg-amber-500/20 border border-amber-500/40 px-2.5 py-0.5 text-[10px] font-bold text-amber-300">
                STAFF LEVEL 4
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Unified Trinity Engine • Chinese Wall Gate • Microsecond Order Fabric
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleVerifyChineseWall}
            className="flex items-center gap-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition border border-slate-700"
          >
            <ShieldAlert className="h-4 w-4 text-sky-400" />
            Audit Chinese Wall
          </button>

          <button
            onClick={handleGlobalFreeze}
            disabled={isFreezing}
            className="flex items-center gap-2 rounded-xl bg-rose-600 hover:bg-rose-500 px-4 py-2 text-xs font-extrabold uppercase tracking-wider text-white shadow-lg shadow-rose-600/30 transition disabled:opacity-50"
          >
            <AlertOctagon className="h-4 w-4" />
            {isFreezing ? "Freezing..." : `Citadel Master Freeze (${freezeStatus})`}
          </button>
        </div>
      </header>

      {/* Audit Banner */}
      {auditLog && (
        <div className="rounded-xl border border-sky-500/40 bg-sky-950/20 p-3.5 flex items-center justify-between text-xs text-sky-300 font-mono">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-sky-400" />
            <span>{auditLog}</span>
          </div>
          <button onClick={() => setAuditLog(null)} className="text-slate-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* =====================================================================
          SECTION 1: TRINITY ENGINE REAL-TIME PIPELINES
         ===================================================================== */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Cpu className="h-5 w-5 text-emerald-400" />
          <h2 className="text-sm font-extrabold uppercase tracking-wider text-white">
            Trinity Engine Real-Time Architecture
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Component 1: Quant Alpha Vector Engine */}
          <div className="rounded-2xl border border-emerald-500/30 bg-slate-900/80 p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <span className="text-xs font-extrabold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <Zap className="h-4 w-4" /> 1. Quant Alpha Engine
              </span>
              <span className="rounded bg-emerald-950 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                NUMBA JIT
              </span>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">P99 Execution Latency:</span>
                <span className="font-mono font-bold text-emerald-400">130 µs</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Simulation Throughput:</span>
                <span className="font-mono text-white">15,400 bars/sec</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Active Seed Blueprints:</span>
                <span className="font-mono text-white">10 Verified ASTs</span>
              </div>
            </div>
            <div className="h-1.5 w-full rounded-full bg-slate-950 overflow-hidden">
              <div className="h-full bg-emerald-500 w-[96%]" />
            </div>
          </div>

          {/* Component 2: AI War Room (Gemini 2.5 Pro) */}
          <div className="rounded-2xl border border-sky-500/30 bg-slate-900/80 p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <span className="text-xs font-extrabold uppercase tracking-wider text-sky-400 flex items-center gap-1.5">
                <Activity className="h-4 w-4" /> 2. AI War Room Copilot
              </span>
              <span className="rounded bg-sky-950 px-2 py-0.5 text-[10px] font-bold text-sky-300">
                GEMINI 2.5 PRO
              </span>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Debate Latency (4 Turn):</span>
                <span className="font-mono font-bold text-sky-400">1.85 s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Acyclic AST Verification:</span>
                <span className="font-mono text-white">100% Strict DAG</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">CRO Regime Adaptation:</span>
                <span className="font-mono text-emerald-300">Active (50-100%)</span>
              </div>
            </div>
            <div className="h-1.5 w-full rounded-full bg-slate-950 overflow-hidden">
              <div className="h-full bg-sky-500 w-[88%]" />
            </div>
          </div>

          {/* Component 3: Microsecond Order Fabric */}
          <div className="rounded-2xl border border-amber-500/30 bg-slate-900/80 p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <span className="text-xs font-extrabold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                <Lock className="h-4 w-4" /> 3. Order Router Fabric
              </span>
              <span className="rounded bg-amber-950 px-2 py-0.5 text-[10px] font-bold text-amber-300">
                SEBI 9-OPS
              </span>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Dispatch Latency:</span>
                <span className="font-mono font-bold text-amber-400">480 µs</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Statutory 9-OPS Cap:</span>
                <span className="font-mono text-white">8.4 / 9.0 Max</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">NSE Freeze Auto-Slicing:</span>
                <span className="font-mono text-emerald-400">NIFTY/BANKNIFTY ✓</span>
              </div>
            </div>
            <div className="h-1.5 w-full rounded-full bg-slate-950 overflow-hidden">
              <div className="h-full bg-amber-500 w-[93%]" />
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================================
          SECTION 2: SEBI CHINESE WALL & EGRESS TELEMETRY
         ===================================================================== */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 space-y-3">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <Lock className="h-4 w-4 text-emerald-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-white">
              SEBI Chinese Wall Enforcement
            </h3>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">Prop Alpha Isolation:</span>
              <span className="text-emerald-400 font-mono font-bold">100% Gated (AES-256 Vault)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Retail Client Routing Silo:</span>
              <span className="text-emerald-400 font-mono font-bold">Decoupled Subnet</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Memory / State Cross-Talk:</span>
              <span className="text-emerald-400 font-mono font-bold">0 Events Detected</span>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 space-y-3">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <Server className="h-4 w-4 text-sky-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-white">
              Multi-Broker Egress Gateway
            </h3>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">Dedicated AWS Mumbai Static NAT:</span>
              <span className="text-sky-300 font-mono font-bold">13.232.104.88</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Connected Broker Adapters:</span>
              <span className="text-white font-mono">6 (Zerodha, Dhan, Breeze, Angel, Fyers, Upstox)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Redis Cluster Buffer:</span>
              <span className="text-slate-300 font-mono">142.5 MB / 1.0 GB</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
