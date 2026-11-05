// apps/web/src/components/dag/IndicatorNode.tsx
'use client';

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Activity, Clock } from 'lucide-react';
import { Timeframe } from '@/types/ast';

export interface IndicatorNodeData {
  name: 'RSI' | 'SUPERTREND' | 'EMA' | 'SMA' | 'VWAP' | 'BOLLINGER' | 'ATR' | 'OI_CHANGE';
  timeframe: Timeframe;
  params: Record<string, number | string | boolean>;
}

export const IndicatorNode = memo(({ id, data, selected }: NodeProps<IndicatorNodeData>) => {
  return (
    <div
      className={`w-64 rounded-lg bg-zinc-900 border transition-all shadow-xl ${
        selected ? 'border-sky-500 shadow-sky-500/20 ring-1 ring-sky-500' : 'border-zinc-800'
      }`}
    >
      {/* Target handle: Incoming Universe/Price Data */}
      <Handle
        type="target"
        position={Position.Left}
        id="price_in"
        className="!w-3 !h-3 !bg-zinc-500 !border-2 !border-zinc-900 !-left-1.5"
      />

      <div className="flex items-center justify-between px-3.5 py-2.5 bg-zinc-950/80 border-b border-zinc-800/80 rounded-t-lg">
        <div className="flex items-center space-x-2">
          <Activity className="w-4 h-4 text-sky-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
            {data.name || 'INDICATOR'}
          </span>
        </div>
        <div className="flex items-center space-x-1 text-[10px] bg-sky-950 text-sky-300 font-mono px-1.5 py-0.5 rounded border border-sky-800">
          <Clock className="w-3 h-3 text-sky-400" />
          <span>{data.timeframe || '5m'}</span>
        </div>
      </div>

      <div className="p-3 space-y-2 text-xs">
        <div className="bg-zinc-950 p-2 rounded border border-zinc-800/80 space-y-1">
          {Object.entries(data.params || {}).map(([key, val]) => (
            <div key={key} className="flex justify-between items-center text-[11px] font-mono">
              <span className="text-zinc-500">{key}:</span>
              <span className="text-sky-300 font-semibold">{String(val)}</span>
            </div>
          ))}
          {(!data.params || Object.keys(data.params).length === 0) && (
            <span className="text-[11px] text-zinc-500 italic font-mono">Default parameters</span>
          )}
        </div>
      </div>

      {/* Outgoing Calculated Value Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="val_out"
        className="!w-3 !h-3 !bg-sky-500 !border-2 !border-zinc-900 !-right-1.5"
      />
    </div>
  );
});

IndicatorNode.displayName = 'IndicatorNode';
