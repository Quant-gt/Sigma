"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  KeyRound,
  Server,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Eye,
  GitFork,
  Award,
  RefreshCw,
  Activity,
} from "lucide-react";
import PreMarketWarRoom from "@/components/ai/PreMarketWarRoom";

interface BrokerSessionCard {
  id: string;
  brokerName: "ZERODHA KITE" | "DHAN HQ" | "ICICI BREEZE";
  clientCode: string;
  staticIp: string;
  ipWhitelisted: boolean;
  sessionStatus: "EXPIRED_0330_IST" | "ACTIVE_2FA_VERIFIED";
  opsQuotaUsed: string;
}

interface MarketplaceStrategy {
  id: string;
  title: string;
  creatorName: string;
  classification: "WHITE_BOX_BLUEPRINT" | "BLACK_BOX_SEBI_RA";
  sebiRaRegNo?: string;
  astSha256: string;
  underlying: string;
  verifiedLiveSharpe: number;
  maxDrawdownPct: number;
  monthlyFeeInr: number;
  subscribers: number;
}

const initialBrokers: BrokerSessionCard[] = [
  {
    id: "brk-1",
    brokerName: "ZERODHA KITE",
    clientCode: "ZS8492",
    staticIp: "13.232.104.88",
    ipWhitelisted: true,
    sessionStatus: "ACTIVE_2FA_VERIFIED",
    opsQuotaUsed: "1.2 / 9.0 OPS",
  },
  {
    id: "brk-2",
    brokerName: "ICICI BREEZE",
    clientCode: "ISEC99210",
    staticIp: "13.232.104.88",
    ipWhitelisted: true,
    sessionStatus: "EXPIRED_0330_IST",
    opsQuotaUsed: "0.0 / 1.25 OPS (75/min)",
  },
  {
    id: "brk-3",
    brokerName: "DHAN HQ",
    clientCode: "110049281",
    staticIp: "13.232.104.88",
    ipWhitelisted: true,
    sessionStatus: "ACTIVE_2FA_VERIFIED",
    opsQuotaUsed: "0.8 / 9.0 OPS",
  },
];

const marketplaceStrategies: MarketplaceStrategy[] = [
  {
    id: "strat-wb-01",
    title: "Nifty 9:20 Dynamic VWAP + SuperTrend Strangle",
    creatorName: "SigmaQuant Labs",
    classification: "WHITE_BOX_BLUEPRINT",
    astSha256: "e3b0c44298fc1c149afbf4c8996fb924",
    underlying: "NIFTY (Weekly F&O)",
    verifiedLiveSharpe: 2.41,
    maxDrawdownPct: 4.8,
    monthlyFeeInr: 0,
    subscribers: 1420,
  },
  {
    id: "strat-bb-02",
    title: "Gamma Scalper Intraday Vol-Surface Arbitrage",
    creatorName: "Aegis Quant Advisory LLP",
    classification: "BLACK_BOX_SEBI_RA",
    sebiRaRegNo: "INH000014829",
    astSha256: "8f434346648f6b96df89dda901c5176b",
    underlying: "BANKNIFTY + NIFTY",
    verifiedLiveSharpe: 3.12,
    maxDrawdownPct: 3.2,
    monthlyFeeInr: 4999,
    subscribers: 385,
  },
];

export default function QuantraCommandCenterPage() {
  const [brokers, setBrokers] = useState<BrokerSessionCard[]>(initialBrokers);
  const [selectedTab, setSelectedTab] = useState<"ALL" | "WHITE_BOX" | "BLACK_BOX">("ALL");

  const renewDaily2FASession = (brokerId: string) => {
    setBrokers((prev) =>
      prev.map((b) =>
        b.id === brokerId ? { ...b, sessionStatus: "ACTIVE_2FA_VERIFIED" } : b
      )
    );
  };

  const filteredStrategies = marketplaceStrategies.filter((s) => {
    if (selectedTab === "WHITE_BOX") return s.classification === "WHITE_BOX_BLUEPRINT";
    if (selectedTab === "BLACK_BOX") return s.classification === "BLACK_BOX_SEBI_RA";
    return true;
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-8">
      {/* =====================================================================
          SECTION 1: 08:45 AM IST PRE-MARKET 2FA & STATIC IP READINESS ENGINE
         ===================================================================== */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4 mb-6">
          <div>
            <div className="flex items-center gap-2">
              <KeyRound className="h-5 w-5 text-amber-400" />
              <h2 className="text-lg font-extrabold tracking-tight text-white">
                08:45 AM IST Morning Readiness Ritual (SEBI Daily 2FA Mandate)
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              All retail API sessions expire daily. Verify your Static Egress IP and complete OAuth 2FA before the 09:15 AM NSE bell.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 text-xs font-mono text-emerald-300">
              <Server className="h-3.5 w-3.5" />
              Dedicated Egress NAT: 13.232.104.88
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {brokers.map((brk) => {
            const isReady = brk.sessionStatus === "ACTIVE_2FA_VERIFIED";
            return (
              <div
                key={brk.id}
                className={`rounded-xl border p-4 transition ${
                  isReady
                    ? "border-emerald-500/30 bg-slate-950/80"
                    : "border-amber-500/50 bg-amber-950/10"
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      {brk.brokerName}
                    </span>
                    <p className="font-mono text-xs text-slate-500">Client ID: {brk.clientCode}</p>
                  </div>
                  {isReady ? (
                    <span className="flex items-center gap-1 rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-[11px] font-bold text-emerald-300">
                      <CheckCircle2 className="h-3.5 w-3.5" /> 2FA READY
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 rounded-full bg-amber-500/20 px-2.5 py-0.5 text-[11px] font-bold text-amber-300">
                      <AlertTriangle className="h-3.5 w-3.5" /> 2FA EXPIRED
                    </span>
                  )}
                </div>

                <div className="space-y-1.5 text-xs border-t border-slate-800/80 pt-3 mb-4">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Whitelisted Static IP:</span>
                    <span className="font-mono text-emerald-400">{brk.staticIp} ✓</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">SEBI Rate Throttler:</span>
                    <span className="font-mono text-slate-300">{brk.opsQuotaUsed}</span>
                  </div>
                </div>

                <button
                  onClick={() => renewDaily2FASession(brk.id)}
                  disabled={isReady}
                  className={`w-full flex items-center justify-center gap-2 rounded-lg py-2 text-xs font-bold transition ${
                    isReady
                      ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                      : "bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-lg shadow-amber-500/20"
                  }`}
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  {isReady ? "Session Authenticated for Today" : "One-Click OAuth 2FA Handshake"}
                </button>
              </div>
            );
          })}
        </div>
      </section>

      {/* =====================================================================
          SECTION 2: 08:45 AM TRADINGAGENTS AI PRE-MARKET WAR ROOM
         ===================================================================== */}
      <section>
        <PreMarketWarRoom />
      </section>

      {/* =====================================================================
          SECTION 3: SEBI-COMPLIANT CREATOR MARKETPLACE (WHITE-BOX VS BLACK-BOX)
         ===================================================================== */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4 mb-6">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-sky-400" />
              <h2 className="text-lg font-extrabold tracking-tight text-white">
                Verified Strategy Marketplace (SEBI White-Box & RA Black-Box Split)
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Every strategy performance badge is cryptographically hashed from real broker contract logs—zero fake paper-trade screenshots.
            </p>
          </div>

          <div className="flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs font-semibold">
            <button
              onClick={() => setSelectedTab("ALL")}
              className={`px-3 py-1.5 rounded-md transition ${
                selectedTab === "ALL" ? "bg-slate-800 text-white" : "text-slate-400"
              }`}
            >
              All Strategies
            </button>
            <button
              onClick={() => setSelectedTab("WHITE_BOX")}
              className={`px-3 py-1.5 rounded-md transition ${
                selectedTab === "WHITE_BOX" ? "bg-emerald-600 text-white" : "text-slate-400"
              }`}
            >
              White-Box Blueprints (Open DAG)
            </button>
            <button
              onClick={() => setSelectedTab("BLACK_BOX")}
              className={`px-3 py-1.5 rounded-md transition ${
                selectedTab === "BLACK_BOX" ? "bg-indigo-600 text-white" : "text-slate-400"
              }`}
            >
              SEBI RA Black-Box Vaults
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {filteredStrategies.map((strat) => {
            const isWhiteBox = strat.classification === "WHITE_BOX_BLUEPRINT";
            return (
              <div
                key={strat.id}
                className="rounded-xl border border-slate-800 bg-slate-950/90 p-5 flex flex-col justify-between hover:border-slate-700 transition"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    {isWhiteBox ? (
                      <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-3 py-0.5 text-[11px] font-bold text-emerald-300">
                        <Eye className="h-3.5 w-3.5" /> WHITE-BOX (100% Transparent Logic)
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5 rounded-full bg-indigo-500/15 border border-indigo-500/30 px-3 py-0.5 text-[11px] font-bold text-indigo-300">
                        <Lock className="h-3.5 w-3.5" /> BLACK-BOX (SEBI RA: {strat.sebiRaRegNo})
                      </span>
                    )}
                    <span className="font-mono text-[11px] text-slate-500">
                      AST SHA256: {strat.astSha256.slice(0, 10)}...
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-white mb-1">{strat.title}</h3>
                  <p className="text-xs text-slate-400 mb-4">
                    By <span className="text-slate-200 font-semibold">{strat.creatorName}</span> •{" "}
                    <span className="text-sky-400 font-mono">{strat.underlying}</span>
                  </p>

                  {/* Broker-Verified Live Metrics */}
                  <div className="grid grid-cols-3 gap-3 rounded-lg bg-slate-900/90 p-3 border border-slate-800/80 mb-4">
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 block">
                        Broker-Verified Sharpe
                      </span>
                      <span className="font-mono text-sm font-bold text-emerald-400 flex items-center gap-1">
                        <Activity className="h-3.5 w-3.5" /> {strat.verifiedLiveSharpe}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 block">
                        Max Drawdown
                      </span>
                      <span className="font-mono text-sm font-bold text-rose-400">
                        -{strat.maxDrawdownPct}%
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 block">
                        Active Deployments
                      </span>
                      <span className="font-mono text-sm font-bold text-slate-200">
                        {strat.subscribers} Traders
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between border-t border-slate-800 pt-4">
                  <div>
                    <span className="text-[10px] uppercase text-slate-400 block">Access Tier</span>
                    <span className="text-sm font-extrabold text-white">
                      {strat.monthlyFeeInr === 0 ? "FREE TEMPLATE" : `₹${strat.monthlyFeeInr}/mo`}
                    </span>
                  </div>

                  {isWhiteBox ? (
                    <button className="flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 px-4 py-2 text-xs font-bold text-white transition">
                      <GitFork className="h-4 w-4" />
                      Inspect & Fork DAG into Studio
                    </button>
                  ) : (
                    <button className="flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 py-2 text-xs font-bold text-white transition">
                      <Award className="h-4 w-4" />
                      Subscribe to Verified RA Signal
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
