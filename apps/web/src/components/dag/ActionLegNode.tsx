// apps/web/src/components/dag/ActionLegNode.tsx
'use client';

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { ShieldCheck, Crosshair, TrendingUp, RefreshCw } from 'lucide-react';
import { ActionType, InstrumentType, OptionType, StrikeSelectionMode } from '@/types/ast';

export interface ActionLegNodeData {
  underlying: string;
  instrumentType: InstrumentType;
  optionType?: OptionType;
  action: ActionType;
  lots: number;
  strikeMode: StrikeSelectionMode;
  strikeOffset: number;
  targetPointsOrPct: number;
  stopLossPointsOrPct: number;
  trailingSlJump?: number;
  moveSlToCost: boolean;
  reEntryCount: number;
}

export const ActionLegNode = memo(({ id, data, selected }: NodeProps<ActionLegNodeData>) => {
  const isBuy = data.action === 'BUY';

  return (
    <div
      className={`w-72 rounded-lg bg-zinc-900 border transition-all shadow-xl ${
        selected ? 'border-rose-500 shadow-rose-500/20 ring-1 ring-rose-500' : 'border-zinc-800'
      }`}
    >
      {/* Target handle: Incoming Entry/Exit Signal */}
      <Handle
        type="target"
        position={Position.Left}
        id="trigger_in"
        className="!w-3 !h-3 !bg-rose-500 !border-2 !border-zinc-900 !-left-1.5"
      />

      <div className="flex items-center justify-between px-3.5 py-2.5 bg-zinc-950/80 border-b border-zinc-800/80 rounded-t-lg">
        <div className="flex items-center space-x-2">
          <Crosshair className="w-4 h-4 text-rose-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
            {data.underlying || 'NIFTY'} LEG
          </span>
        </div>
        <span
          className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold border ${
            isBuy
              ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
              : 'bg-rose-950 text-rose-400 border-rose-800'
          }`}
        >
          {data.action} {data.lots || 1} LOT
        </span>
      </div>

      <div className="p-3 space-y-2 text-xs">
        <div className="flex justify-between items-center text-[11px] font-mono bg-zinc-950 px-2 py-1.5 rounded border border-zinc-800/80">
          <span className="text-zinc-400">Instrument:</span>
          <span className="text-zinc-200 font-bold">
            {data.strikeMode} {data.optionType ? `(${data.optionType})` : ''}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
          <div className="bg-zinc-950 p-1.5 rounded border border-zinc-800/80">
            <span className="text-zinc-500 block text-[10px]">TARGET</span>
            <span className="text-emerald-400 font-bold">+{data.targetPointsOrPct || 40} pts</span>
          </div>
          <div className="bg-zinc-950 p-1.5 rounded border border-zinc-800/80">
            <span className="text-zinc-500 block text-[10px]">STOP LOSS</span>
            <span className="text-rose-400 font-bold">-{data.stopLossPointsOrPct || 20} pts</span>
          </div>
        </div>

        <div className="space-y-1 pt-1 border-t border-zinc-800/80 text-[10px] text-zinc-400 font-mono">
          {data.trailingSlJump && (
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1">
                <TrendingUp className="w-3 h-3 text-sky-400" /> Trailing SL:
              </span>
              <span className="text-zinc-200">+{data.trailingSlJump} pts</span>
            </div>
          )}
          {data.moveSlToCost && (
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-emerald-400" /> SL to Cost:
              </span>
              <span className="text-emerald-400">ENABLED</span>
            </div>
          )}
          {data.reEntryCount > 0 && (
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1">
                <RefreshCw className="w-3 h-3 text-amber-400" /> Re-entries:
              </span>
              <span className="text-amber-400">{data.reEntryCount} max</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

ActionLegNode.displayName = 'ActionLegNode';
