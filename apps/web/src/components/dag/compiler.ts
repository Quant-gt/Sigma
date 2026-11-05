// apps/web/src/components/dag/compiler.ts
// Strict React Flow Graph -> Canonical JSON AST Compiler & Cycle Detector

import { Edge, Node } from '@xyflow/react';
import {
  ActionLegConfig,
  ActionLegNodeData,
  IndicatorConfig,
  IndicatorNodeData,
  LogicGateNode,
  LogicGateNodeData,
  MathFormulaNodeData,
  Timeframe,
  VisualDAGAST,
} from '@/types/ast';

export interface CompilationResult {
  success: boolean;
  ast?: VisualDAGAST;
  sha256Hash?: string;
  errors: string[];
}

/**
 * Computes deterministic SHA-256 hash in browser using SubtleCrypto
 */
async function computeSha256(content: string): Promise<string> {
  if (typeof window !== 'undefined' && window.crypto && window.crypto.subtle) {
    const encoder = new TextEncoder();
    const data = encoder.encode(content);
    const hashBuffer = await window.crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
  }
  return 'fallback-hash-' + Date.now();
}

/**
 * Compiles visual React Flow nodes and edges into canonical JSON AST.
 */
export async function compileReactFlowToAST(
  strategyId: string,
  strategyName: string,
  baseTimeframe: Timeframe,
  nodes: Node[],
  edges: Edge[],
  authorEmail: string,
  sebiRaNumber?: string,
  isBlackBoxVault: boolean = false
): Promise<CompilationResult> {
  const errors: string[] = [];

  // 1. Filter Nodes by Type
  const indicatorNodes = nodes.filter((n) => n.type === 'indicatorNode');
  const formulaNodes = nodes.filter((n) => n.type === 'mathFormulaNode');
  const logicNodes = nodes.filter((n) => n.type === 'logicGateNode');
  const actionLegNodes = nodes.filter((n) => n.type === 'actionLegNode');

  if (actionLegNodes.length === 0) {
    errors.push('Strategy must have at least one Action Leg node connected.');
  }

  // 2. Identify Entry Gate (the logic gate connected to action legs)
  const incomingToActionEdges = edges.filter((e) =>
    actionLegNodes.some((leg) => leg.id === e.target)
  );

  if (incomingToActionEdges.length === 0) {
    errors.push('No Logic Gate is connected to trigger the Action Leg(s).');
  }

  const entryGateId = incomingToActionEdges[0]?.source || '';

  // 3. Cycle Detection using DFS on Edges
  const adjList: Map<string, string[]> = new Map();
  nodes.forEach((n) => adjList.set(n.id, []));
  edges.forEach((e) => {
    if (adjList.has(e.source)) {
      adjList.get(e.source)?.push(e.target);
    }
  });

  const visited: Map<string, number> = new Map(); // 0 = unvisited, 1 = visiting, 2 = visited
  nodes.forEach((n) => visited.set(n.id, 0));

  let hasCycle = false;
  let cycleNode = '';

  function dfs(nodeId: string) {
    visited.set(nodeId, 1);
    const neighbors = adjList.get(nodeId) || [];
    for (const neighbor of neighbors) {
      if (visited.get(neighbor) === 1) {
        hasCycle = true;
        cycleNode = neighbor;
        return;
      }
      if (visited.get(neighbor) === 0) {
        dfs(neighbor);
      }
    }
    visited.set(nodeId, 2);
  }

  for (const node of nodes) {
    if (visited.get(node.id) === 0) {
      dfs(node.id);
      if (hasCycle) break;
    }
  }

  if (hasCycle) {
    errors.push(`Cyclic dependency detected involving node '${cycleNode}'. Strategy DAG must be acyclic.`);
  }

  if (errors.length > 0) {
    return { success: false, errors };
  }

  // 4. Map React Flow nodes to Canonical AST definitions
  const indicators: IndicatorNodeData[] = indicatorNodes.map((n) => {
    const d = n.data as IndicatorNodeData;
    return {
      id: n.id,
      name: d.name || 'RSI',
      timeframe: d.timeframe || baseTimeframe,
      params: d.params || {},
    };
  });

  const formulas: MathFormulaNodeData[] = formulaNodes.map((n) => {
    const d = n.data as MathFormulaNodeData;
    return {
      id: n.id,
      expression: d.expression || '',
    };
  });

  const logicGates: LogicGateNodeData[] = logicNodes.map((n) => {
    const d = n.data as LogicGateNodeData;
    // Find left & right source operands from incoming edges
    const incomingEdges = edges.filter((e) => e.target === n.id);
    const leftEdge = incomingEdges.find((e) => e.targetHandle === 'left') || incomingEdges[0];
    const rightEdge = incomingEdges.find((e) => e.targetHandle === 'right') || incomingEdges[1];

    return {
      id: n.id,
      operator: d.operator || 'AND',
      leftOperandNodeId: leftEdge?.source || '',
      rightOperandNodeId: rightEdge?.source || '',
      sequenceCandleWindow: d.sequenceCandleWindow,
    };
  });

  const actionLegs: ActionLegNodeData[] = actionLegNodes.map((n) => {
    const d = n.data as ActionLegNodeData;
    return {
      id: n.id,
      underlying: d.underlying || 'NIFTY',
      instrumentType: d.instrumentType || 'INDEX_OPT',
      optionType: d.optionType || 'CE',
      action: d.action || 'BUY',
      lots: d.lots || 1,
      strikeMode: d.strikeMode || 'ATM',
      strikeOffset: d.strikeOffset || 0,
      targetPointsOrPct: d.targetPointsOrPct || 40,
      stopLossPointsOrPct: d.stopLossPointsOrPct || 20,
      trailingSlJump: d.trailingSlJump,
      moveSlToCost: d.moveSlToCost ?? false,
      reEntryCount: d.reEntryCount || 0,
    };
  });

  const ast: VisualDAGAST = {
    version: '2.0.0',
    strategyId,
    strategyName,
    baseTimeframe,
    indicators,
    formulas,
    logicGates,
    entryGateId,
    actionLegs,
    metadata: {
      author: authorEmail,
      sebiRaRegNo: sebiRaNumber,
      isBlackBoxVault,
      compiledAt: new Date().toISOString(),
    },
  };

  const astJsonString = JSON.stringify(ast, null, 2);
  const sha256Hash = await computeSha256(astJsonString);

  return {
    success: true,
    ast,
    sha256Hash,
    errors: [],
  };
}
