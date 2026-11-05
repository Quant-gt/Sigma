// apps/web/src/components/dag/DAGStudioCanvas.tsx
'use client';

import React, { useCallback, useMemo, useState } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  Node,
  Edge,
  OnNodesChange,
  OnEdgesChange,
  OnConnect,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { UniverseNode } from './UniverseNode';
import { IndicatorNode } from './IndicatorNode';
import { MathFormulaNode } from './MathFormulaNode';
import { LogicGateNode } from './LogicGateNode';
import { ActionLegNode } from './ActionLegNode';
import { compileReactFlowToAST, CompilationResult } from './compiler';
import { Play, Save, AlertCircle, CheckCircle2, Plus } from 'lucide-react';

const initialNodes: Node[] = [
  {
    id: 'u1',
    type: 'universeNode',
    position: { x: 50, y: 150 },
    data: { universeType: 'NIFTY_50', segment: 'OPTIONS', expiryType: 'CURRENT_WEEK' },
  },
  {
    id: 'i1',
    type: 'indicatorNode',
    position: { x: 380, y: 80 },
    data: { name: 'RSI', timeframe: '5m', params: { period: 14, overbought: 70, oversold: 30 } },
  },
  {
    id: 'i2',
    type: 'indicatorNode',
    position: { x: 380, y: 260 },
    data: { name: 'SUPERTREND', timeframe: '5m', params: { period: 10, multiplier: 3.0 } },
  },
  {
    id: 'g1',
    type: 'logicGateNode',
    position: { x: 720, y: 160 },
    data: { operator: 'AND' },
  },
  {
    id: 'leg1',
    type: 'actionLegNode',
    position: { x: 1040, y: 140 },
    data: {
      underlying: 'NIFTY',
      instrumentType: 'INDEX_OPT',
      optionType: 'CE',
      action: 'BUY',
      lots: 2,
      strikeMode: 'ATM',
      strikeOffset: 0,
      targetPointsOrPct: 50,
      stopLossPointsOrPct: 25,
      trailingSlJump: 10,
      moveSlToCost: true,
      reEntryCount: 1,
    },
  },
];

const initialEdges: Edge[] = [
  { id: 'e1', source: 'u1', target: 'i1', sourceHandle: 'universe_out', targetHandle: 'price_in' },
  { id: 'e2', source: 'u1', target: 'i2', sourceHandle: 'universe_out', targetHandle: 'price_in' },
  { id: 'e3', source: 'i1', target: 'g1', sourceHandle: 'val_out', targetHandle: 'left' },
  { id: 'e4', source: 'i2', target: 'g1', sourceHandle: 'val_out', targetHandle: 'right' },
  { id: 'e5', source: 'g1', target: 'leg1', sourceHandle: 'signal_out', targetHandle: 'trigger_in' },
];

export const DAGStudioCanvas: React.FC<{ strategyId: string; strategyName: string }> = ({
  strategyId,
  strategyName,
}) => {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [compilation, setCompilation] = useState<CompilationResult | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const nodeTypes = useMemo(
    () => ({
      universeNode: UniverseNode,
      indicatorNode: IndicatorNode,
      mathFormulaNode: MathFormulaNode,
      logicGateNode: LogicGateNode,
      actionLegNode: ActionLegNode,
    }),
    []
  );

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onConnect: OnConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, animated: true }, eds)),
    []
  );

  const handleCompileAndSave = async () => {
    setIsSaving(true);
    const result = await compileReactFlowToAST(
      strategyId,
      strategyName,
      '5m',
      nodes,
      edges,
      'trader@sigmaspire.com'
    );
    setCompilation(result);
    setIsSaving(false);
  };

  const addNode = (type: string) => {
    const id = `${type}_${Date.now()}`;
    const newNode: Node = {
      id,
      type,
      position: { x: 400 + Math.random() * 100, y: 200 + Math.random() * 100 },
      data:
        type === 'indicatorNode'
          ? { name: 'EMA', timeframe: '5m', params: { period: 20 } }
          : type === 'logicGateNode'
          ? { operator: 'CROSSOVER' }
          : type === 'mathFormulaNode'
          ? { expression: '(CLOSE - VWAP) / ATR(14)' }
          : { underlying: 'NIFTY', action: 'BUY', lots: 1 },
    };
    setNodes((nds) => [...nds, newNode]);
  };

  return (
    <div className="w-full h-[calc(100vh-60px)] bg-zinc-950 flex flex-col">
      {/* Studio Toolbar */}
      <div className="h-14 border-b border-zinc-800 bg-zinc-900/60 px-6 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="font-semibold text-sm text-zinc-100">{strategyName}</div>
          <span className="text-[11px] bg-zinc-800 px-2 py-0.5 rounded text-zinc-400 font-mono">
            DAG v2.0
          </span>
        </div>

        {/* Node Addition Quick Bar */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => addNode('indicatorNode')}
            className="flex items-center space-x-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 text-sky-300 px-2.5 py-1.5 rounded transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Indicator</span>
          </button>
          <button
            onClick={() => addNode('logicGateNode')}
            className="flex items-center space-x-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 text-amber-300 px-2.5 py-1.5 rounded transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Logic Gate</span>
          </button>
          <button
            onClick={() => addNode('mathFormulaNode')}
            className="flex items-center space-x-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 text-purple-300 px-2.5 py-1.5 rounded transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Math Node</span>
          </button>
          <button
            onClick={() => addNode('actionLegNode')}
            className="flex items-center space-x-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 text-rose-300 px-2.5 py-1.5 rounded transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Action Leg</span>
          </button>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-3">
          <button
            onClick={handleCompileAndSave}
            disabled={isSaving}
            className="flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2 rounded-md transition shadow"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{isSaving ? 'Compiling...' : 'Compile & Save AST'}</span>
          </button>
        </div>
      </div>

      {/* Compiler Validation Banner */}
      {compilation && (
        <div
          className={`px-6 py-2 text-xs flex items-center justify-between border-b ${
            compilation.success
              ? 'bg-emerald-950/60 border-emerald-800/80 text-emerald-300'
              : 'bg-red-950/60 border-red-800/80 text-red-300'
          }`}
        >
          <div className="flex items-center space-x-2">
            {compilation.success ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-400" />
            )}
            <span>
              {compilation.success
                ? `Strategy DAG compiled successfully! SHA-256 Hash: ${compilation.sha256Hash?.slice(0, 16)}...`
                : `Compilation failed: ${compilation.errors.join(' | ')}`}
            </span>
          </div>
        </div>
      )}

      {/* React Flow Viewport Canvas */}
      <div className="flex-1 w-full h-full">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
          className="bg-zinc-950"
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#27272a" />
          <Controls className="!bg-zinc-900 !border-zinc-800 !text-zinc-200 fill-zinc-200" />
        </ReactFlow>
      </div>
    </div>
  );
};
