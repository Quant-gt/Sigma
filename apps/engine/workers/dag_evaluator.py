# apps/engine/workers/dag_evaluator.py
# Sub-millisecond Strategy DAG AST Evaluator

from typing import Dict, List, Optional, Tuple
from apps.api.app.schemas.ast_schema import (
    StrategyAST,
    LogicGateNode,
)


class DAGEvaluator:
    """
    In-memory, sub-millisecond evaluator for compiled JSON Strategy ASTs.
    Evaluates rolling indicators, formulas, and logic gates on incoming tick/candle frames.
    """

    def __init__(self, ast: StrategyAST):
        self.ast = ast
        self.gates_by_id: Dict[str, LogicGateNode] = {
            n.node_id: n for n in ast.nodes if getattr(n, "node_type", "") == "LOGIC_GATE"
        }

    def evaluate_entry_signal(
        self,
        current_indicator_values: Dict[str, float],
        previous_indicator_values: Dict[str, float],
        candle_history_booleans: Optional[Dict[str, List[bool]]] = None
    ) -> bool:
        """
        Recursively evaluates the Entry Gate node.
        Returns True if the DAG resolves to an active execution signal.
        """
        return self._evaluate_node(
            node_id=self.ast.entryGateId,
            curr_vals=current_indicator_values,
            prev_vals=previous_indicator_values,
            candle_history=candle_history_booleans or {}
        )

    def _evaluate_node(
        self,
        node_id: str,
        curr_vals: Dict[str, float],
        prev_vals: Dict[str, float],
        candle_history: Dict[str, List[bool]]
    ) -> bool:
        if node_id in self.gates_by_id:
            gate = self.gates_by_id[node_id]
            left_id = gate.leftOperandNodeId
            right_id = gate.rightOperandNodeId

            if gate.operator == "AND":
                return self._evaluate_node(left_id, curr_vals, prev_vals, candle_history) and \
                       self._evaluate_node(right_id, curr_vals, prev_vals, candle_history)

            elif gate.operator == "OR":
                return self._evaluate_node(left_id, curr_vals, prev_vals, candle_history) or \
                       self._evaluate_node(right_id, curr_vals, prev_vals, candle_history)

            elif gate.operator == "NOT":
                return not self._evaluate_node(left_id, curr_vals, prev_vals, candle_history)

            elif gate.operator == "CROSSOVER":
                # Left crossed above Right: Left_prev <= Right_prev and Left_curr > Right_curr
                l_curr = curr_vals.get(left_id, 0.0)
                l_prev = prev_vals.get(left_id, 0.0)
                r_curr = curr_vals.get(right_id, 0.0)
                r_prev = prev_vals.get(right_id, 0.0)
                return (l_prev <= r_prev) and (l_curr > r_curr)

            elif gate.operator == "CROSSUNDER":
                # Left crossed below Right: Left_prev >= Right_prev and Left_curr < Right_curr
                l_curr = curr_vals.get(left_id, 0.0)
                l_prev = prev_vals.get(left_id, 0.0)
                r_curr = curr_vals.get(right_id, 0.0)
                r_prev = prev_vals.get(right_id, 0.0)
                return (l_prev >= r_prev) and (l_curr < r_curr)

            elif gate.operator == "SEQUENCE":
                # Condition A followed by Condition B within N candles
                window = gate.sequenceCandleWindow or 3
                history = candle_history.get(left_id, [])
                condition_a_occurred = any(history[-window:]) if history else False
                condition_b_now = self._evaluate_node(right_id, curr_vals, prev_vals, candle_history)
                return condition_a_occurred and condition_b_now

        # Leaf node evaluation (direct boolean or threshold comparison)
        return bool(curr_vals.get(node_id, 0.0))
