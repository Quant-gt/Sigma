# apps/api/app/routers/vibe.py
from __future__ import annotations
from collections import defaultdict, deque
from typing import Any, Dict, List, Tuple
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from apps.api.app.schemas.ast_schema import StrategyAST

router = APIRouter(prefix="/api/v1/vibe", tags=["Vibe-to-DAG Copilot"])


class VibePromptRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=10,
        max_length=1500,
        examples=[
            "Sell 1 lot Nifty weekly ATM CE and PE at 09:20 when 5m SuperTrend(10,3) is above VWAP. Set 25% SL, trail SL by 5% for every 10% move, and square off at 15:15."
        ],
    )
    current_ast: StrategyAST | None = None


class ReactFlowGraphResponse(BaseModel):
    ast: StrategyAST
    ast_sha256: str
    react_flow_nodes: List[Dict[str, Any]]
    react_flow_edges: List[Dict[str, Any]]
    compiler_summary: str


def compute_topological_react_flow_layout(
    ast: StrategyAST,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Computes deterministic left-to-right (X, Y) coordinates for React Flow nodes
    using Kahn's topological layering so AI-generated graphs never overlap on canvas.
    """
    in_degree: Dict[str, int] = {n.node_id: 0 for n in ast.nodes}
    adj: Dict[str, List[str]] = defaultdict(list)

    for edge in ast.edges:
        adj[edge.source].append(edge.target)
        in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

    queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
    depth_map: Dict[str, int] = {nid: 0 for nid in queue}

    while queue:
        curr = queue.popleft()
        for nxt in adj[curr]:
            depth_map[nxt] = max(depth_map.get(nxt, 0), depth_map[curr] + 1)
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    # Group nodes by column depth for clean vertical spacing
    columns: Dict[int, List[str]] = defaultdict(list)
    for nid, depth in depth_map.items():
        columns[depth].append(nid)

    ui_type_map = {
        "UNIVERSE": "universeNode",
        "INDICATOR": "indicatorNode",
        "CONSTANT": "indicatorNode",
        "COMPARISON": "logicGateNode",
        "LOGIC_GATE": "logicGateNode",
        "ACTION_LEG": "actionLegNode",
    }

    node_lookup = {n.node_id: n for n in ast.nodes}
    rf_nodes: List[Dict[str, Any]] = []

    for col_idx, node_ids in columns.items():
        x_pos = 60 + col_idx * 320
        for row_idx, nid in enumerate(node_ids):
            y_pos = 80 + row_idx * 180
            ast_node = node_lookup[nid]
            rf_nodes.append(
                {
                    "id": nid,
                    "type": ui_type_map.get(ast_node.node_type, "indicatorNode"),
                    "position": {"x": x_pos, "y": y_pos},
                    "data": ast_node.model_dump(mode="json"),
                }
            )

    rf_edges = [
        {"id": e.id, "source": e.source, "target": e.target, "animated": True}
        for e in ast.edges
    ]
    return rf_nodes, rf_edges


SYSTEM_INSTRUCTION = """
You are the Quantra v2 Vibe-Trading AST Architect for Indian NSE/BSE Markets.
Translate the user's natural language trading prompt into a strictly valid `StrategyAST` JSON object.
CRITICAL RULES:
1. NSE 2026 Lot Sizes: NIFTY = 65, BANKNIFTY = 30, FINNIFTY = 60, MIDCPNIFTY = 120, SENSEX = 20.
2. Every graph MUST start with a `UNIVERSE` node, connect through `INDICATOR`, `COMPARISON`, or `LOGIC_GATE` nodes, and terminate in one or more `ACTION_LEG` nodes.
3. Every `ACTION_LEG` MUST include a valid `risk_config` (stop_loss_value > 0) and `mpp_slippage_bps` (default 50) for SEBI Market Price Protection compliance.
4. Graph must be strictly acyclic (DAG).
"""


@router.post("/compile-prompt", response_model=ReactFlowGraphResponse)
async def compile_vibe_prompt_to_dag(req: VibePromptRequest) -> ReactFlowGraphResponse:
    client = genai.Client()

    user_context = req.prompt
    if req.current_ast:
        user_context += f"\n\nModify this existing StrategyAST JSON:\n{req.current_ast.model_dump_json()}"

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=user_context,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=StrategyAST,
            temperature=0.1,
        ),
    )

    try:
        validated_ast = StrategyAST.model_validate_json(response.text)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"AST Validation / Cycle Check Failed: {exc}"
        ) from exc

    rf_nodes, rf_edges = compute_topological_react_flow_layout(validated_ast)
    leg_count = sum(1 for n in validated_ast.nodes if n.node_type == "ACTION_LEG")

    return ReactFlowGraphResponse(
        ast=validated_ast,
        ast_sha256=validated_ast.compute_cryptographic_hash(),
        react_flow_nodes=rf_nodes,
        react_flow_edges=rf_edges,
        compiler_summary=(
            f"Compiled '{validated_ast.strategy_name}' with {len(validated_ast.nodes)} DAG nodes, "
            f"{leg_count} SEBI-MPP protected F&O action legs, and 0 cyclic dependencies."
        ),
    )
