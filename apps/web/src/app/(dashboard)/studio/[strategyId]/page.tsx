"use client";

import React, { useState, useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  Connection,
  Edge,
  Node,
  NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ShieldAlert, Play, Save, Cpu, Layers, GitMerge, Zap, Sparkles, PanelLeftOpen, PanelLeftClose } from "lucide-react";
import VibePromptSidebar from "@/components/dag/VibePromptSidebar";

// ============================================================================
// 1. CUSTOM NODE: UNIVERSE & DYNAMIC OPTION STRIKE NODE
// ============================================================================
export function UniverseCustomNode({ data }: NodeProps) {
  return (
    <div className="w-64 rounded-xl border border-emerald-500/40 bg-slate-900/95 p-3 shadow-xl backdrop-blur-md text-slate-100">
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 mb-2">
        <Layers className="h-4 w-4 text-emerald-400" />
        <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
          Universe & Expiry
        </span>
      </div>
      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-slate-400">Underlying:</span>
          <span className="font-mono font-semibold text-white">{String(data.underlying || "NIFTY")}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Segment:</span>
          <span className="font-mono text-emerald-300">{String(data.segment || "NSE_FNO")}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Expiry:</span>
          <span className="rounded bg-emerald-950 px-1.5 py-0.5 text-[10px] text-emerald-300">
            {String(data.expiry_type || "WEEKLY_CURRENT")}
          </span>
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!h-3 !w-3 !bg-emerald-400 !border-2 !border-slate-950"
      />
    </div>
  );
}

// ============================================================================
// 2. CUSTOM NODE: MULTI-TIMEFRAME TECHNICAL INDICATOR
// ============================================================================
export function IndicatorCustomNode({ data }: NodeProps) {
  return (
    <div className="w-64 rounded-xl border border-sky-500/40 bg-slate-900/95 p-3 shadow-xl text-slate-100">
      <Handle
        type="target"
        position={Position.Left}
        className="!h-3 !w-3 !bg-sky-400 !border-2 !border-slate-950"
      />
      <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
        <div className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-sky-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-sky-400">
            {String(data.indicator || "SUPERTREND")}
          </span>
        </div>
        <span className="rounded bg-sky-950 px-1.5 py-0.5 font-mono text-[10px] text-sky-300">
          {String(data.timeframe || "5m")}
        </span>
      </div>
      <div className="text-xs text-slate-300 font-mono bg-slate-950/70 p-2 rounded border border-slate-800">
        Params: {JSON.stringify(data.params || { period: 10, multiplier: 3 })}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!h-3 !w-3 !bg-sky-400 !border-2 !border-slate-950"
      />
    </div>
  );
}

// ============================================================================
// 3. CUSTOM NODE: LOGIC GATE / CROSSOVER COMPARATOR
// ============================================================================
export function LogicGateCustomNode({ data }: NodeProps) {
  return (
    <div className="w-56 rounded-xl border border-amber-500/40 bg-slate-900/95 p-3 shadow-xl text-slate-100">
      <Handle
        type="target"
        position={Position.Left}
        className="!h-3 !w-3 !bg-amber-400 !border-2 !border-slate-950"
      />
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 mb-2">
        <GitMerge className="h-4 w-4 text-amber-400" />
        <span className="text-xs font-bold uppercase tracking-wider text-amber-400">
          Condition Gate
        </span>
      </div>
      <div className="text-center py-1.5 rounded bg-amber-950/50 border border-amber-500/30 font-mono text-xs font-bold text-amber-300">
        {String(data.operator || "CROSSES_BELOW")}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!h-3 !w-3 !bg-amber-400 !border-2 !border-slate-950"
      />
    </div>
  );
}

// ============================================================================
// 4. CUSTOM NODE: MULTI-LEG F&O EXECUTION ACTION NODE
// ============================================================================
export function ActionLegCustomNode({ data }: NodeProps) {
  const isSell = data.side === "SELL";
  return (
    <div
      className={`w-72 rounded-xl border ${
        isSell ? "border-rose-500/50" : "border-indigo-500/50"
      } bg-slate-900/95 p-3 shadow-xl text-slate-100`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!h-3 !w-3 !bg-rose-400 !border-2 !border-slate-950"
      />
      <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
        <div className="flex items-center gap-1.5">
          <Zap className="h-4 w-4 text-rose-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-white">
            F&O Action Leg
          </span>
        </div>
        <span
          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
            isSell ? "bg-rose-600 text-white" : "bg-emerald-600 text-white"
          }`}
        >
          {String(data.side || "SELL")} {String(data.option_type || "CE")}
        </span>
      </div>

      <div className="space-y-1.5 text-xs">
        <div className="flex justify-between">
          <span className="text-slate-400">Strike Selection:</span>
          <span className="font-mono text-amber-300">{String(data.strike_label || "ATM (Offset 0)")}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Stop Loss / TSL:</span>
          <span className="font-mono text-rose-300">
            {String(data.sl_pct || "25%")} | TSL: {data.tsl ? "ON" : "OFF"}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">SEBI MPP Protection:</span>
          <span className="font-mono text-emerald-400">{String(data.mpp_bps || 50)} bps Limit</span>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN STUDIO COMPONENT WITH DAG COMPILER & KILL SWITCH
// ============================================================================
const initialNodes: Node[] = [
  {
    id: "univ-1",
    type: "universeNode",
    position: { x: 40, y: 140 },
    data: { underlying: "NIFTY", segment: "NSE_FNO", expiry_type: "WEEKLY_CURRENT" },
  },
  {
    id: "ind-1",
    type: "indicatorNode",
    position: { x: 350, y: 60 },
    data: { indicator: "SUPERTREND", timeframe: "5m", params: { period: 10, multiplier: 3 } },
  },
  {
    id: "ind-2",
    type: "indicatorNode",
    position: { x: 350, y: 220 },
    data: { indicator: "VWAP", timeframe: "5m", params: {} },
  },
  {
    id: "gate-1",
    type: "logicGateNode",
    position: { x: 670, y: 140 },
    data: { operator: "CROSSES_BELOW" },
  },
  {
    id: "leg-1",
    type: "actionLegNode",
    position: { x: 960, y: 80 },
    data: {
      side: "SELL",
      option_type: "CE",
      strike_label: "ATM + 1 (OTM)",
      sl_pct: "25%",
      tsl: true,
      mpp_bps: 50,
    },
  },
];

const initialEdges: Edge[] = [
  { id: "e1", source: "univ-1", target: "ind-1", animated: true },
  { id: "e2", source: "univ-1", target: "ind-2", animated: true },
  { id: "e3", source: "ind-1", target: "gate-1", animated: true },
  { id: "e4", source: "ind-2", target: "gate-1", animated: true },
  { id: "e5", source: "gate-1", target: "leg-1", animated: true },
];

export default function QuantraStrategyStudio() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [compiledAstJson, setCompiledAstJson] = useState<string>("");
  const [backtestReport, setBacktestReport] = useState<any>(null);
  const [isBacktesting, setIsBacktesting] = useState<boolean>(false);
  const [killSwitchStatus, setKillSwitchStatus] = useState<string>("ARMED");
  const [showVibeSidebar, setShowVibeSidebar] = useState<boolean>(true);
  const [vibePrompt, setVibePrompt] = useState<string>(
    "Sell 1 lot Nifty weekly ATM CE and PE at 09:20 when 5m SuperTrend(10,3) is above VWAP. Set 25% SL, trail SL by 5% for every 10% move, and square off at 15:15."
  );
  const [isVibing, setIsVibing] = useState<boolean>(false);
  const [vibeSummary, setVibeSummary] = useState<string>("");

  const handleVibeToDag = async () => {
    if (!vibePrompt.trim()) return;
    setIsVibing(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/vibe/compile-prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: vibePrompt }),
      });
      if (res.ok) {
        const data = await res.json();
        setNodes(data.react_flow_nodes);
        setEdges(data.react_flow_edges);
        setCompiledAstJson(JSON.stringify(data.ast, null, 2));
        setVibeSummary(data.compiler_summary);
      }
    } catch (err) {
      console.error("Vibe compiler error:", err);
    } finally {
      setIsVibing(false);
    }
  };

  const handleApplyCompiledGraph = (newNodes: Node[], newEdges: Edge[], hash: string) => {
    setNodes(newNodes);
    setEdges(newEdges);
  };

  const nodeTypes = useMemo(
    () => ({
      universeNode: UniverseCustomNode,
      indicatorNode: IndicatorCustomNode,
      logicGateNode: LogicGateCustomNode,
      actionLegNode: ActionLegCustomNode,
    }),
    []
  );

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true }, eds)),
    [setEdges]
  );

  // Compile Visual Graph into Canonical JSON AST for Backend Validation
  const compileToAST = () => {
    const astPayload = {
      schema_version: "2.0.0",
      strategy_name: "Nifty 5m SuperTrend + VWAP Short Straddle",
      entry_time_ist: "09:16:00",
      square_off_time_ist: "15:15:00",
      max_strategy_loss_inr: "10000.00",
      nodes: nodes.map((n) => ({
        node_id: n.id,
        node_type: n.type === "universeNode" ? "UNIVERSE" : n.type === "indicatorNode" ? "INDICATOR" : n.type === "logicGateNode" ? "LOGIC_GATE" : "ACTION_LEG",
        trigger_node_id: "gate-1",
        universe_node_id: "univ-1",
        side: "SELL",
        lots: 1,
        underlying: "NIFTY",
        segment: "NSE_FNO",
        indicator: "SUPERTREND",
        timeframe: "5m",
        params: { period: 10, multiplier: 3.0 },
        candle_offset: 0,
        risk_config: {
          stop_loss_type: "PERCENT",
          stop_loss_value: "25.0",
          target_type: "PERCENT",
          target_value: "50.0",
          trailing_sl_enabled: true,
          trail_step_Move: "10.0",
          trail_sl_by: "5.0",
          move_sl_to_cost_on_other_leg_sl: true,
          max_reentries_on_sl: 1
        },
        mpp_slippage_bps: 50
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
      })),
    };
    const jsonStr = JSON.stringify(astPayload, null, 2);
    setCompiledAstJson(jsonStr);
    return astPayload;
  };

  // Run Vectorized Backtest API
  const handleRunBacktest = async () => {
    setIsBacktesting(true);
    try {
      const ast = compileToAST();
      const res = await fetch("http://localhost:8000/api/v1/backtest/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategyAst: ast,
          initialCapital: 500000.0,
          slippageBps: 50.0
        })
      });
      if (res.ok) {
        const data = await res.json();
        setBacktestReport(data);
      }
    } catch (err) {
      console.error("Backtest API error:", err);
    } finally {
      setIsBacktesting(false);
    }
  };

  // Trigger Atomic SEBI Kill Switch
  const triggerEmergencyKillSwitch = async () => {
    setKillSwitchStatus("HALTING_ALL_BROKERS...");
    try {
      await fetch("http://localhost:8000/api/v1/risk/kill-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: "u1", reason: "Manual Emergency Trigger" })
      });
      setKillSwitchStatus("ALL_POSITIONS_SQUARED_OFF");
    } catch {
      setKillSwitchStatus("KILL_SWITCH_LOCKED");
    }
  };

  return (
    <div className="flex h-screen w-full flex-col bg-slate-950 text-slate-100">
      {/* Top Command Header */}
      <header className="flex items-center justify-between border-b border-slate-800 bg-slate-900/80 px-6 py-3">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setShowVibeSidebar(!showVibeSidebar)}
            className="flex items-center gap-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 px-2.5 py-1.5 text-xs text-slate-300 transition"
            title="Toggle Vibe AI Sidebar"
          >
            {showVibeSidebar ? (
              <PanelLeftClose className="h-4 w-4 text-emerald-400" />
            ) : (
              <PanelLeftOpen className="h-4 w-4 text-emerald-400" />
            )}
            <span className="font-semibold text-[11px]">AI Copilot</span>
          </button>
          <span className="text-lg font-extrabold tracking-tight text-white">
            QUANTRA <span className="text-xs font-mono text-emerald-400">v2.0 AST STUDIO</span>
          </span>
          <span className="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-3 py-0.5 text-xs text-emerald-300">
            SEBI Static IP: 13.232.104.88 (Verified)
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={compileToAST}
            className="flex items-center gap-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 px-3.5 py-2 text-xs font-semibold text-slate-200 transition"
          >
            <Save className="h-4 w-4 text-sky-400" />
            Compile & Validate AST
          </button>

          <button
            onClick={handleRunBacktest}
            disabled={isBacktesting}
            className="flex items-center gap-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 px-4 py-2 text-xs font-bold text-white transition disabled:opacity-50"
          >
            <Play className="h-4 w-4" />
            {isBacktesting ? "Simulating Numba..." : "Run Vector Backtest"}
          </button>

          {/* Emergency Kill Switch */}
          <button
            onClick={triggerEmergencyKillSwitch}
            className="flex items-center gap-2 rounded-lg bg-rose-600 hover:bg-rose-500 px-4 py-2 text-xs font-extrabold uppercase tracking-wider text-white shadow-lg shadow-rose-600/30 transition"
          >
            <ShieldAlert className="h-4 w-4" />
            Kill Switch ({killSwitchStatus})
          </button>
        </div>
      </header>

      {/* AI Vibe-to-DAG Copilot Prompt Bar */}
      <div className="flex items-center gap-3 border-b border-slate-800 bg-slate-900/40 px-6 py-2.5 backdrop-blur-sm">
        <div className="flex items-center gap-1.5 text-xs font-bold text-violet-400 shrink-0">
          <Sparkles className="h-4 w-4 text-violet-400 animate-pulse" />
          <span>VIBE-TO-DAG:</span>
        </div>
        <input
          type="text"
          value={vibePrompt}
          onChange={(e) => setVibePrompt(e.target.value)}
          placeholder="Describe your strategy in natural language (e.g. Sell 1 lot Nifty ATM straddle on 5m SuperTrend crossover)..."
          className="flex-1 rounded-lg border border-slate-700 bg-slate-950/80 px-3.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 font-mono"
        />
        <button
          onClick={handleVibeToDag}
          disabled={isVibing}
          className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 px-4 py-1.5 text-xs font-bold text-white shadow-md shadow-violet-600/20 transition disabled:opacity-50 shrink-0"
        >
          <Sparkles className="h-3.5 w-3.5" />
          {isVibing ? "Gemini Compiling..." : "Generate Graph"}
        </button>
        {vibeSummary && (
          <span className="text-[11px] text-emerald-400 font-mono hidden md:inline truncate max-w-sm">
            {vibeSummary}
          </span>
        )}
      </div>

      {/* Main Split Studio */}
      <div className="flex flex-1 overflow-hidden">
        {showVibeSidebar && (
          <VibePromptSidebar onApplyCompiledGraph={handleApplyCompiledGraph} />
        )}
        <div className="flex-1 h-full">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background color="#1e293b" gap={20} />
            <Controls className="!bg-slate-900 !border-slate-800" />
            <MiniMap className="!bg-slate-900" nodeColor="#38bdf8" />
          </ReactFlow>
        </div>

        {/* Right Drawer: Backtest Report */}
        {backtestReport && (
          <aside className="w-96 border-l border-slate-800 bg-slate-900/95 p-4 overflow-y-auto">
            <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                Numba Vector Backtest Report
              </h3>
              <button
                onClick={() => setBacktestReport(null)}
                className="text-xs text-slate-400 hover:text-white"
              >
                Close
              </button>
            </div>

            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-400 block uppercase">Sharpe Ratio</span>
                  <span className="text-emerald-400 font-bold font-mono text-sm">{backtestReport.metrics.sharpeRatio}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-400 block uppercase">Win Rate</span>
                  <span className="text-white font-bold font-mono text-sm">{backtestReport.metrics.winRatePct}%</span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-400 block uppercase">Net P&L (INR)</span>
                  <span className={`font-bold font-mono text-sm ${backtestReport.metrics.netPnlInr >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                    ₹{backtestReport.metrics.netPnlInr.toLocaleString()}
                  </span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-400 block uppercase">Max Drawdown</span>
                  <span className="text-rose-400 font-bold font-mono text-sm">-{backtestReport.metrics.maxDrawdownPct}%</span>
                </div>
              </div>

              <div className="text-xs text-slate-400 bg-slate-950 p-2.5 rounded border border-slate-800 space-y-1 font-mono">
                <div className="flex justify-between">
                  <span>Total Trades:</span>
                  <span className="text-slate-200">{backtestReport.metrics.totalTrades}</span>
                </div>
                <div className="flex justify-between">
                  <span>Gross P&L:</span>
                  <span className="text-slate-200">₹{backtestReport.metrics.grossPnlInr.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Statutory Taxes:</span>
                  <span className="text-rose-300">₹{backtestReport.metrics.totalStatutoryChargesInr.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Sortino Ratio:</span>
                  <span className="text-slate-200">{backtestReport.metrics.sortinoRatio}</span>
                </div>
              </div>
            </div>
          </aside>
        )}

        {/* Right Drawer: Compiled AST Inspector */}
        {compiledAstJson && (
          <aside className="w-96 border-l border-slate-800 bg-slate-900/95 p-4 overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-sky-400">
                Compiled JSON AST Output
              </h3>
              <button
                onClick={() => setCompiledAstJson("")}
                className="text-xs text-slate-400 hover:text-white"
              >
                Close
              </button>
            </div>
            <pre className="rounded-lg bg-slate-950 p-3 font-mono text-[11px] text-emerald-300 overflow-x-auto border border-slate-800">
              {compiledAstJson}
            </pre>
          </aside>
        )}
      </div>
    </div>
  );
}
