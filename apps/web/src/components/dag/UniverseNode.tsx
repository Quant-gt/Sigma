// apps/web/src/components/dag/UniverseNode.tsx
'use client';

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Globe, Layers } from 'lucide-react';

export interface UniverseNodeData {
  universeType: 'NIFTY_50' | 'NIFTY_BANK' | 'NIFTY_NEXT_50' | 'NIFTY_500' | 'CUSTOM_WATCHLIST';
  segment: 'EQUITY' | 'FUTURES' | 'OPTIONS';
  symbols?: string[];
  expiryType?: 'CURRENT_WEEK' | 'NEXT_WEEK' | 'MONTHLY';
}

export const UniverseNode = memo(({ id, data, selected }: NodeProps<UniverseNodeData>) => {
  return (
    <div
      className={`w-64 rounded-lg bg-zinc-900 border transition-all shadow-xl ${
        selected ? 'border-emerald-500 shadow-emerald-500/20 ring-1 ring-emerald-500' : 'border-zinc-800'
      }`}
    >
      <div className="flex items-center justify-between px-3.5 py-2.5 bg-zinc-950/80 border-b border-zinc-800/80 rounded-t-lg">
        <div className="flex items-center space-x-2">
          <Globe className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-200">Asset Universe</span>
        </div>
        <span className="text-[10px] bg-emerald-950 text-emerald-300 font-mono px-1.5 py-0.5 rounded border border-emerald-800">
          ROOT
        </span>
      </div>

      <div className="p-3 space-y-2 text-xs">
        <div>
          <label className="text-[11px] text-zinc-400 block mb-1">Index / Universe</label>
          <div className="flex items-center space-x-1.5 bg-zinc-950 px-2.5 py-1.5 rounded border border-zinc-800 text-zinc-200 font-mono">
            <Layers className="w-3.5 h-3.5 text-zinc-500" />
            <span>{data.universeType || 'NIFTY_50'}</span>
          </div>
        </div>

        <div className="flex justify-between items-center text-[11px] pt-1">
          <span className="text-zinc-400">Segment:</span>
          <span className="text-emerald-400 font-semibold font-mono">{data.segment || 'OPTIONS'}</span>
        </div>

        {data.segment === 'OPTIONS' && (
          <div className="flex justify-between items-center text-[11px]">
            <span className="text-zinc-400">Expiry Cycle:</span>
            <span className="text-zinc-300 font-mono">{data.expiryType || 'CURRENT_WEEK'}</span>
          </div>
        )}
      </div>

      {/* Outgoing Asset Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="universe_out"
        className="!w-3 !h-3 !bg-emerald-500 !border-2 !border-zinc-900 !-right-1.5"
      />
    </div>
  );
});

UniverseNode.displayName = 'UniverseNode';
