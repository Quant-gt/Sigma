// apps/web/src/types/ast.ts
// TypeScript contracts matching apps/api/app/schemas/ast_schema.py

export type Timeframe = 'TICK' | '1m' | '3m' | '5m' | '15m' | '1h' | '1d';

export type Segment = 'NSE_EQ' | 'NSE_FNO' | 'BSE_FNO';

export type StrikeSelectionMode = 'ATM_OFFSET' | 'CLOSEST_PREMIUM' | 'CLOSEST_DELTA';

export interface UniverseNode {
  node_id: string;
  node_type: 'UNIVERSE';
  segment: Segment;
  underlying: string;
  expiry_type: 'WEEKLY_CURRENT' | 'WEEKLY_NEXT' | 'MONTHLY';
}

export interface IndicatorNode {
  node_id: string;
  node_type: 'INDICATOR';
  indicator:
    | 'RSI'
    | 'SUPERTREND'
    | 'EMA'
    | 'SMA'
    | 'VWAP'
    | 'ATR'
    | 'BOLLINGER_UPPER'
    | 'BOLLINGER_LOWER'
    | 'OI_CHANGE_PCT'
    | 'IV_RANK';
  timeframe: Timeframe;
  params: Record<string, number>;
  candle_offset: number;
}

export interface ConstantNode {
  node_id: string;
  node_type: 'CONSTANT';
  value: string | number;
}

export interface ComparisonNode {
  node_id: string;
  node_type: 'COMPARISON';
  operator: 'GT' | 'LT' | 'GTE' | 'LTE' | 'EQ' | 'CROSSES_ABOVE' | 'CROSSES_BELOW';
  left_node_id: string;
  right_node_id: string;
}

export interface LogicGateNode {
  node_id: string;
  node_type: 'LOGIC_GATE';
  operator: 'AND' | 'OR' | 'NOT' | 'SEQUENCE_WITHIN_N_CANDLES';
  input_node_ids: string[];
  sequence_window_candles?: number;
}

export interface OptionStrikeConfig {
  option_type: 'CE' | 'PE' | 'FUT';
  selection_mode: StrikeSelectionMode;
  atm_offset_steps: number;
  target_premium?: string | number;
  target_delta?: string | number;
}

export interface RiskLegConfig {
  stop_loss_type: 'PERCENT' | 'POINTS' | 'UNDERLYING_POINTS';
  stop_loss_value: string | number;
  target_type: 'PERCENT' | 'POINTS' | 'NONE';
  target_value?: string | number;
  trailing_sl_enabled: boolean;
  trail_step_Move?: string | number;
  trail_sl_by?: string | number;
  move_sl_to_cost_on_other_leg_sl: boolean;
  max_reentries_on_sl: number;
}

export interface ActionLegNode {
  node_id: string;
  node_type: 'ACTION_LEG';
  trigger_node_id: string;
  universe_node_id: string;
  side: 'BUY' | 'SELL';
  lots: number;
  strike_config?: OptionStrikeConfig;
  risk_config: RiskLegConfig;
  mpp_slippage_bps: number;
}

export type ASTNode =
  | UniverseNode
  | IndicatorNode
  | ConstantNode
  | ComparisonNode
  | LogicGateNode
  | ActionLegNode;

export interface DAGEdge {
  id: string;
  source: string;
  target: string;
}

export interface StrategyAST {
  schema_version: '2.0.0';
  strategy_name: string;
  entry_time_ist: string;
  square_off_time_ist: string;
  max_strategy_loss_inr: string | number;
  max_strategy_profit_inr?: string | number;
  nodes: ASTNode[];
  edges: DAGEdge[];
}
