// apps/web/src/components/dag/LogicGateNode.tsx
'use client';

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { GitMerge, ArrowRightLeft, FastForward } from 'lucide-react';

export interface LogicGateNodeData {
  operator: 'AND' | 'OR' | 'NOT' | 'CROSSOVER' | 'CROSSUNDER' | 'SEQUENCE';
  sequenceCandleWindow?: number;
}

export const LogicGateNode = memo(({ id, data, selected }: NodeProps<LogicGateNodeData>) => {
  const isSequence = data.operator === 'SEQUENCE';
  const isCrossover = data.operator === 'CROSSOVER' || data.operator === 'CROSSUNDER';

  return (
    <div
      className={`w-60 rounded-lg bg-zinc-900 border transition-all shadow-xl ${
        selected ? 'border-amber-500 shadow-amber-500/20 ring-1 ring-amber-500' : 'border-zinc-800'
      }`}
    >
      {/* Target handle 1: Left Operand */}
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        style={{ top: '35%' }}
        className="!w-3 !h-3 !bg-amber-400 !border-2 !border-zinc-900 !-left-1.5"
      />
      
      {/* Target handle 2: Right Operand (optional for NOT) */}
      {data.operator !== 'NOT' && (
        <Handle
          type="target"
          position={Position.Left}
          id="right"
          style={{ top: '65%' }}
          className="!w-3 !h-3 !bg-amber-600 !border-2 !border-zinc-900 !-left-1.5"
        />
      )}

      <div className="flex items-center justify-between px-3.5 py-2.5 bg-zinc-950/80 border-b border-zinc-800/80 rounded-t-lg">
        <div className="flex items-center space-x-2">
          {isSequence ? (
            <FastForward className="w-4 h-4 text-amber-400" />
          ) : isCrossover ? (
            <ArrowRightLeft className="w-4 h-4 text-amber-400" />
          ) : (
            <GitMerge className="w-4 h-4 text-amber-400" />
          )}
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
            {data.operator || 'AND'} GATE
          </span>
        </div>
        <span className="text-[10px] bg-amber-950 text-amber-300 font-mono px-1.5 py-0.5 rounded border border-amber-800">
          LOGIC
        </span>
      </div>

      <div className="p-3 space-y-1.5 text-xs">
        <div className="flex justify-between items-center text-[11px] font-mono">
          <span className="text-zinc-500">Operation:</span>
          <span className="text-amber-400 font-bold">{data.operator}</span>
        </div>

        {isSequence && (
          <div className="flex justify-between items-center text-[11px] font-mono pt-1 border-t border-zinc-800">
            <span className="text-zinc-500">Window Bars:</span>
            <span className="text-zinc-200 font-semibold">{data.sequenceCandleWindow || 3} candles</span>
          </div>
        )}
      </div>

      {/* Outgoing Boolean Signal */}
      <Handle
        type="source"
        position={Position.Right}
        id="signal_out"
        className="!w-3 !h-3 !bg-amber-500 !border-2 !border-zinc-900 !-right-1.5"
      />
    </div>
  );
});

LogicGateNode.displayName = 'LogicGateNode';
