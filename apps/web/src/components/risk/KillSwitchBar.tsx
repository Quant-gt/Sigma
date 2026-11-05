// apps/web/src/components/risk/KillSwitchBar.tsx
'use client';

import React, { useState } from 'react';
import { AlertTriangle, ShieldAlert, Loader2, CheckCircle2 } from 'lucide-react';

interface KillSwitchBarProps {
  userId: string;
  activeAlgoCount: number;
  openPositionCount: number;
}

export const KillSwitchBar: React.FC<KillSwitchBarProps> = ({
  userId,
  activeAlgoCount,
  openPositionCount,
}) => {
  const [isArming, setIsArming] = useState<boolean>(false);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [halted, setHalted] = useState<boolean>(false);

  const handleEmergencyHalt = async () => {
    if (!isArming) {
      setIsArming(true);
      return;
    }

    setIsExecuting(true);
    try {
      const res = await fetch('/api/v1/risk/kill-switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId, reason: 'User Manual Emergency Kill-Switch' }),
      });
      if (res.ok) {
        setHalted(true);
        setIsArming(false);
      }
    } catch (err) {
      console.error('Kill switch network failure:', err);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className={`w-full px-6 py-3 flex items-center justify-between transition-colors duration-300 border-b ${
      halted 
        ? 'bg-red-950 border-red-800 text-red-200' 
        : 'bg-zinc-950 border-zinc-800 text-zinc-100'
    }`}>
      <div className="flex items-center space-x-3">
        <div className={`p-2 rounded-md ${halted ? 'bg-red-900/60' : 'bg-zinc-900'}`}>
          {halted ? (
            <ShieldAlert className="w-5 h-5 text-red-400 animate-pulse" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-amber-500" />
          )}
        </div>
        <div>
          <div className="font-semibold text-sm tracking-wide flex items-center gap-2">
            <span>SEBI Central Risk Firewall</span>
            {halted && (
              <span className="text-xs bg-red-800 px-2 py-0.5 rounded-full font-mono text-white">
                TRADING HALTED
              </span>
            )}
          </div>
          <div className="text-xs text-zinc-400">
            Active Algos: <span className="font-mono text-zinc-200">{activeAlgoCount}</span> | Open Positions: <span className="font-mono text-zinc-200">{openPositionCount}</span>
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {isArming && !halted && (
          <button
            onClick={() => setIsArming(false)}
            className="text-xs text-zinc-400 hover:text-zinc-200 px-3 py-1.5 rounded transition-colors"
          >
            Cancel
          </button>
        )}

        <button
          onClick={handleEmergencyHalt}
          disabled={isExecuting || halted}
          className={`flex items-center space-x-2 text-xs font-bold uppercase tracking-wider px-4 py-2 rounded-md transition-all shadow-md ${
            halted
              ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
              : isArming
              ? 'bg-red-600 hover:bg-red-500 text-white animate-bounce'
              : 'bg-red-950 hover:bg-red-900 text-red-300 border border-red-800'
          }`}
        >
          {isExecuting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Halting All Algos...</span>
            </>
          ) : halted ? (
            <>
              <CheckCircle2 className="w-4 h-4 text-red-400" />
              <span>All Systems Stopped</span>
            </>
          ) : isArming ? (
            <span>CONFIRM EMERGENCY HALT</span>
          ) : (
            <span>ACTIVATE KILL-SWITCH</span>
          )}
        </button>
      </div>
    </div>
  );
};
