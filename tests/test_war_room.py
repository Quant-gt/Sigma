# tests/test_war_room.py
import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath("."))

from apps.api.app.services.trading_agents_warroom import (
    MarketTelemetrySnapshot,
    TradingAgentsWarRoomService,
)


def run_war_room_tests():
    print("[+] Testing TradingAgentsWarRoomService Multi-Agent Debate Engine...")

    # Scenario 1: Low Vol Theta Decay (Nifty at 24200, VIX 13.5, PCR 1.05)
    t1 = MarketTelemetrySnapshot(
        underlying="NIFTY",
        spot_close=24200.0,
        gift_nifty_gap_pts=10.0,
        india_vix=13.5,
        vix_change_pct=-1.2,
        pcr_oi=1.05,
        max_pain_strike=24200,
        call_wall_strike=24500,
        put_wall_strike=24000,
        fii_net_index_fut_long_pct=48.0,
        atr_14_daily=140.0,
        rsi_14_daily=52.0,
    )
    v1 = asyncio.run(TradingAgentsWarRoomService.run_morning_committee(t1))
    assert v1.regime_classification == "LOW_VOL_THETA_DECAY"
    assert v1.recommended_lot_multiplier_scale == 1.0
    assert len(v1.debate_transcript) == 4
    print("  [OK] Low Vol Theta Decay passed. Scale: 1.0x, Blueprints:", v1.recommended_whitebox_blueprints[0])

    # Scenario 2: High VIX Event Danger (India VIX 21.5)
    t2 = MarketTelemetrySnapshot(
        underlying="BANKNIFTY",
        spot_close=51200.0,
        gift_nifty_gap_pts=220.0,
        india_vix=21.5,
        vix_change_pct=+15.4,
        pcr_oi=0.92,
        max_pain_strike=51000,
        call_wall_strike=52000,
        put_wall_strike=50000,
        fii_net_index_fut_long_pct=50.0,
        atr_14_daily=550.0,
        rsi_14_daily=61.0,
    )
    v2 = asyncio.run(TradingAgentsWarRoomService.run_morning_committee(t2))
    assert v2.regime_classification == "HIGH_VIX_EVENT_DANGER"
    assert v2.recommended_lot_multiplier_scale == 0.5
    print("  [OK] High VIX Event Danger passed. CRO enforced 50% lot scaling.")

    # Scenario 3: Bullish Momentum Breakout (PCR 1.25, FII Long 62%)
    t3 = MarketTelemetrySnapshot(
        underlying="NIFTY",
        spot_close=24350.0,
        gift_nifty_gap_pts=55.0,
        india_vix=14.0,
        vix_change_pct=-3.0,
        pcr_oi=1.28,
        max_pain_strike=24300,
        call_wall_strike=24600,
        put_wall_strike=24200,
        fii_net_index_fut_long_pct=62.0,
        atr_14_daily=170.0,
        rsi_14_daily=64.0,
    )
    v3 = asyncio.run(TradingAgentsWarRoomService.run_morning_committee(t3))
    assert v3.regime_classification == "BULLISH_MOMENTUM_BREAKOUT"
    assert v3.bull_probability_pct == 55
    print("  [OK] Bullish Momentum Breakout passed. Bull prob: 55%.")

    print("ALL TRADINGAGENTS WAR ROOM TESTS PASSED!")


if __name__ == "__main__":
    run_war_room_tests()
