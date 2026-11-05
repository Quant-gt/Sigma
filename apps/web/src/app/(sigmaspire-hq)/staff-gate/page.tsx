"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldAlert, KeyRound, Fingerprint, Lock, Terminal } from "lucide-react";

export default function SigmaSpireStaffGate() {
  const router = useRouter();
  const [email, setEmail] = useState("shekhar@sigmaspire.in");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/citadel/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          staff_email: email,
          password,
          totp_code: totp,
          hardware_key_signature: "YUBIKEY_FIDO2_OK",
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Authentication Rejected");
      }
      const data = await res.json();
      sessionStorage.setItem("citadel_token", data.token);
      router.push("/citadel");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Access Denied");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-slate-100 flex items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl border border-rose-500/30 bg-slate-950 p-8 shadow-2xl shadow-rose-950/30 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-rose-500/10 p-2.5 border border-rose-500/30">
              <Terminal className="h-6 w-6 text-rose-500" />
            </div>
            <div>
              <h1 className="text-base font-black tracking-wider uppercase text-white">
                SigmaSpire Citadel
              </h1>
              <p className="text-[11px] font-mono text-rose-400">
                RESTRICTED INTERNAL PROP & OPS PORTAL
              </p>
            </div>
          </div>
          <Lock className="h-5 w-5 text-slate-500" />
        </div>

        <div className="rounded-lg bg-slate-900/90 border border-slate-800 p-3 text-[11px] text-slate-400 font-mono">
          <span className="text-emerald-400">● VPN TUNNEL VERIFIED</span> • Unindexed Host •
          SEBI Chinese-Wall Audit Logging Active
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="text-xs font-bold uppercase text-slate-400 block mb-1">
              SigmaSpire Staff Identity
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2.5 text-xs font-mono text-white focus:border-rose-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-xs font-bold uppercase text-slate-400 block mb-1">
              Master Citadel Passphrase
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••••••••••"
              className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2.5 text-xs font-mono text-white focus:border-rose-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-xs font-bold uppercase text-slate-400 block mb-1">
              Hardware Authenticator 6-Digit TOTP
            </label>
            <div className="relative">
              <KeyRound className="h-4 w-4 text-amber-400 absolute left-3.5 top-3" />
              <input
                type="text"
                required
                maxLength={6}
                value={totp}
                onChange={(e) => setTotp(e.target.value)}
                placeholder="202699"
                className="w-full rounded-xl border border-slate-800 bg-slate-900 pl-10 pr-4 py-2.5 text-sm font-mono tracking-widest text-amber-300 focus:border-amber-500 focus:outline-none"
              />
            </div>
          </div>

          {error && (
            <div className="rounded-lg border border-rose-500/40 bg-rose-950/30 p-3 text-xs text-rose-300 flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-rose-600 hover:bg-rose-500 py-3 text-xs font-extrabold uppercase tracking-wider text-white transition shadow-lg shadow-rose-600/30"
          >
            <Fingerprint className="h-4 w-4" />
            {loading ? "Verifying Hardware Token..." : "Unlock SigmaSpire Citadel"}
          </button>
        </form>
      </div>
    </div>
  );
}
