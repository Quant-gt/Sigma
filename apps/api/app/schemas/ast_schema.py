from __future__ import annotations
from decimal import Decimal
from enum import Enum
from typing import Annotated, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, model_validator
import hashlib
import json


class Timeframe(str, Enum):
    TICK = "TICK"
    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    D1 = "1d"


class Segment(str, Enum):
    NSE_EQ = "NSE_EQ"
    NSE_FNO = "NSE_FNO"
    BSE_FNO = "BSE_FNO"


class StrikeSelectionMode(str, Enum):
    ATM_OFFSET = "ATM_OFFSET"          # e.g., ATM + 2 strikes (OTM2) or ATM - 1 (ITM1)
    CLOSEST_PREMIUM = "CLOSEST_PREMIUM" # e.g., Strike with premium closest to ₹50
    CLOSEST_DELTA = "CLOSEST_DELTA"     # e.g., Strike with Delta closest to 0.30


# --- DAG NODE DEFINITIONS ---

class UniverseNode(BaseModel):
    node_id: str
    node_type: Literal["UNIVERSE"] = "UNIVERSE"
    segment: Segment
    underlying: str = Field(..., examples=["NIFTY", "BANKNIFTY", "RELIANCE"])
    expiry_type: Literal["WEEKLY_CURRENT", "WEEKLY_NEXT", "MONTHLY"] = "WEEKLY_CURRENT"


class IndicatorNode(BaseModel):
    node_id: str
    node_type: Literal["INDICATOR"] = "INDICATOR"
    indicator: Literal[
        "RSI", "SUPERTREND", "EMA", "SMA", "VWAP", 
        "ATR", "BOLLINGER_UPPER", "BOLLINGER_LOWER", "OI_CHANGE_PCT", "IV_RANK"
    ]
    timeframe: Timeframe
    params: Dict[str, Union[int, float]] = Field(default_factory=dict, examples=[{"period": 14, "multiplier": 3.0}])
    candle_offset: int = Field(default=0, ge=0, le=50, description="0 = live/current candle, 1 = previous closed candle")


class ConstantNode(BaseModel):
    node_id: str
    node_type: Literal["CONSTANT"] = "CONSTANT"
    value: Decimal


class ComparisonNode(BaseModel):
    node_id: str
    node_type: Literal["COMPARISON"] = "COMPARISON"
    operator: Literal["GT", "LT", "GTE", "LTE", "EQ", "CROSSES_ABOVE", "CROSSES_BELOW"]
    left_node_id: str
    right_node_id: str


class LogicGateNode(BaseModel):
    node_id: str
    node_type: Literal["LOGIC_GATE"] = "LOGIC_GATE"
    operator: Literal["AND", "OR", "NOT", "SEQUENCE_WITHIN_N_CANDLES"]
    input_node_ids: List[str] = Field(..., min_length=1)
    sequence_window_candles: Optional[int] = Field(default=None, ge=1, le=20)


class OptionStrikeConfig(BaseModel):
    option_type: Literal["CE", "PE", "FUT"]
    selection_mode: StrikeSelectionMode = StrikeSelectionMode.ATM_OFFSET
    atm_offset_steps: int = Field(default=0, ge=-20, le=20)
    target_premium: Optional[Decimal] = None
    target_delta: Optional[Decimal] = None


class RiskLegConfig(BaseModel):
    stop_loss_type: Literal["PERCENT", "POINTS", "UNDERLYING_POINTS"] = "PERCENT"
    stop_loss_value: Decimal = Field(..., gt=Decimal("0"))
    target_type: Literal["PERCENT", "POINTS", "NONE"] = "PERCENT"
    target_value: Optional[Decimal] = None
    trailing_sl_enabled: bool = False
    trail_step_Move: Optional[Decimal] = None  # For every X move in favor...
    trail_sl_by: Optional[Decimal] = None      # ...trail SL by Y
    move_sl_to_cost_on_other_leg_sl: bool = True
    max_reentries_on_sl: int = Field(default=0, ge=0, le=5)


class ActionLegNode(BaseModel):
    node_id: str
    node_type: Literal["ACTION_LEG"] = "ACTION_LEG"
    trigger_node_id: str
    universe_node_id: str
    side: Literal["BUY", "SELL"]
    lots: int = Field(default=1, ge=1, le=100)
    strike_config: Optional[OptionStrikeConfig] = None
    risk_config: RiskLegConfig
    mpp_slippage_bps: int = Field(default=50, ge=5, le=300, description="SEBI Market Price Protection limit offset in bps")


ASTNode = Annotated[
    Union[UniverseNode, IndicatorNode, ConstantNode, ComparisonNode, LogicGateNode, ActionLegNode],
    Field(discriminator="node_type")
]


class DAGEdge(BaseModel):
    id: str
    source: str
    target: str


class StrategyAST(BaseModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    strategy_name: str
    entry_time_ist: str = Field(default="09:16:00", pattern=r"^\d{2}:\d{2}:\d{2}$")
    square_off_time_ist: str = Field(default="15:15:00", pattern=r"^\d{2}:\d{2}:\d{2}$")
    max_strategy_loss_inr: Decimal = Field(default=Decimal("5000.00"))
    max_strategy_profit_inr: Optional[Decimal] = None
    nodes: List[ASTNode]
    edges: List[DAGEdge]

    @model_validator(mode="after")
    def validate_dag_acyclic_and_integrity(self) -> "StrategyAST":
        node_map = {n.node_id: n for n in self.nodes}
        
        # 1. Verify all edge endpoints exist
        adj: Dict[str, List[str]] = {n.node_id: [] for n in self.nodes}
        for edge in self.edges:
            if edge.source not in node_map or edge.target not in node_map:
                raise ValueError(f"Edge {edge.id} references non-existent node.")
            adj[edge.source].append(edge.target)

        # 2. Kahn's / DFS Cycle Detection (Strict DAG Guarantee)
        visited: Dict[str, int] = {n_id: 0 for n_id in node_map}  # 0=unvisited, 1=visiting, 2=visited

        def has_cycle(curr: str) -> bool:
            visited[curr] = 1
            for neighbor in adj[curr]:
                if visited[neighbor] == 1:
                    return True
                if visited[neighbor] == 0 and has_cycle(neighbor):
                    return True
            visited[curr] = 2
            return False

        for node_id in node_map:
            if visited[node_id] == 0:
                if has_cycle(node_id):
                    raise ValueError("Invalid Strategy Graph: Cyclic dependency detected in DAG.")

        # 3. Ensure at least one ActionLegNode exists
        if not any(isinstance(n, ActionLegNode) for n in self.nodes):
            raise ValueError("Strategy must contain at least one ActionLegNode.")

        return self

    def compute_cryptographic_hash(self) -> str:
        """Generates deterministic SHA-256 hash for Creator IP Verification."""
        canonical_json = json.dumps(self.model_dump(mode="json"), sort_keys=True)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
