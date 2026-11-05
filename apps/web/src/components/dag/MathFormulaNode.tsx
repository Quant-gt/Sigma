// apps/web/src/components/dag/MathFormulaNode.tsx
'use client';

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Calculator } from 'lucide-react';

export interface MathFormulaNodeData {
  expression: string;
  variableMap?: Record<string, string>; // e.g. { A: 'node_indicator_1', B: 'node_indicator_2' }
}

export const MathFormulaNode = memo(({ id, data, selected }: NodeProps<MathFormulaNodeData>) => {
  return (
    <div
      className={`w-64 rounded-lg bg-zinc-900 border transition-all shadow-xl ${
        selected ? 'border-purple-500 shadow-purple-500/20 ring-1 ring-purple-500' : 'border-zinc-800'
      }`}
    >
      {/* Dynamic input operand handles */}
      <Handle
        type="target"
        position={Position.Left}
        id="operand_a"
        style={{ top: '35%' }}
        className="!w-3 !h-3 !bg-purple-400 !border-2 !border-zinc-900 !-left-1.5"
      />
      <Handle
        type="target"
        position={Position.Left}
        id="operand_b"
        style={{ top: '65%' }}
        className="!w-3 !h-3 !bg-purple-600 !border-2 !border-zinc-900 !-left-1.5"
      />

      <div className="flex items-center justify-between px-3.5 py-2.5 bg-zinc-950/80 border-b border-zinc-800/80 rounded-t-lg">
        <div className="flex items-center space-x-2">
          <Calculator className="w-4 h-4 text-purple-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-200">Formula Expr</span>
        </div>
        <span className="text-[10px] bg-purple-950 text-purple-300 font-mono px-1.5 py-0.5 rounded border border-purple-800">
          MATH
        </span>
      </div>

      <div className="p-3 space-y-2 text-xs">
        <label className="text-[11px] text-zinc-400 block mb-0.5">Custom Expression</label>
        <div className="bg-zinc-950 p-2 rounded border border-zinc-800 font-mono text-purple-300 text-[11px] break-all">
          {data.expression || '(CLOSE - VWAP) / ATR(14)'}
        </div>
      </div>

      {/* Outgoing calculated value */}
      <Handle
        type="source"
        position={Position.Right}
        id="formula_out"
        className="!w-3 !h-3 !bg-purple-500 !border-2 !border-zinc-900 !-right-1.5"
      />
    </div>
  );
});

MathFormulaNode.displayName = 'MathFormulaNode';
