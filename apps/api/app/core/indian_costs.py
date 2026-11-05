# apps/api/app/core/indian_costs.py
# Fixed-Point Decimal Indian Statutory Transaction Cost Engine (Post-Oct 2024 Finance Act Rules)

from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from pydantic import BaseModel


class TradeInstrumentType(str, Enum):
    EQUITY_DELIVERY = "EQUITY_DELIVERY"
    EQUITY_INTRADAY = "EQUITY_INTRADAY"
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"


class StatutoryCostBreakdown(BaseModel):
    turnover: Decimal
    brokerage: Decimal
    stt_ctt: Decimal
    exchange_turnover_charge: Decimal
    sebi_turnover_fee: Decimal
    stamp_duty: Decimal
    gst_18_pct: Decimal
    total_charges: Decimal
    net_breakeven_points_per_unit: Decimal


class IndianStatutoryCostEngine:
    """
    Exact fixed-point statutory charge calculator for NSE/BSE (Post-Oct 2024 Finance Act rules).
    """
    SEBI_FEE_RATE = Decimal("0.000001")  # ₹10 per Crore (0.0001%)
    GST_RATE = Decimal("0.18")           # 18% on (Brokerage + Exchange + SEBI)

    # NSE True-to-Label Transaction Charges (Oct 2024)
    NSE_EXCHANGE_RATES = {
        TradeInstrumentType.EQUITY_DELIVERY: Decimal("0.0000297"),  # 0.00297%
        TradeInstrumentType.EQUITY_INTRADAY: Decimal("0.0000297"),  # 0.00297%
        TradeInstrumentType.FUTURES: Decimal("0.0000173"),          # 0.00173%
        TradeInstrumentType.OPTIONS: Decimal("0.0003503"),          # 0.03503% (on premium)
    }

    @classmethod
    def calculate_round_trip(
        cls,
        instrument: TradeInstrumentType,
        buy_price: Decimal,
        sell_price: Decimal,
        quantity: int,
        flat_brokerage_per_order: Decimal = Decimal("20.00")
    ) -> StatutoryCostBreakdown:
        qty = Decimal(quantity)
        buy_turnover = (buy_price * qty).quantize(Decimal("0.01"), ROUND_HALF_UP)
        sell_turnover = (sell_price * qty).quantize(Decimal("0.01"), ROUND_HALF_UP)
        total_turnover = buy_turnover + sell_turnover

        # 1. Brokerage (Flat ₹20 per executed leg or 0.03% cap for equity intraday)
        if instrument == TradeInstrumentType.EQUITY_DELIVERY:
            brokerage = Decimal("0.00")
        elif instrument == TradeInstrumentType.OPTIONS:
            brokerage = flat_brokerage_per_order * Decimal("2")
        else:
            buy_brok = min(flat_brokerage_per_order, buy_turnover * Decimal("0.0003"))
            sell_brok = min(flat_brokerage_per_order, sell_turnover * Decimal("0.0003"))
            brokerage = (buy_brok + sell_brok).quantize(Decimal("0.01"), ROUND_HALF_UP)

        # 2. STT (Securities Transaction Tax - Post Oct 1, 2024 Hike)
        if instrument == TradeInstrumentType.EQUITY_DELIVERY:
            stt = total_turnover * Decimal("0.001")          # 0.1% on both Buy & Sell
        elif instrument == TradeInstrumentType.EQUITY_INTRADAY:
            stt = sell_turnover * Decimal("0.00025")         # 0.025% on Sell
        elif instrument == TradeInstrumentType.FUTURES:
            stt = sell_turnover * Decimal("0.0002")          # 0.02% on Sell (Hiked from 0.0125%)
        elif instrument == TradeInstrumentType.OPTIONS:
            stt = sell_turnover * Decimal("0.001")           # 0.10% on Sell Premium (Hiked from 0.0625%)
        stt = stt.quantize(Decimal("1"), ROUND_HALF_UP)      # STT is rounded to nearest rupee

        # 3. Exchange Turnover Charges
        exch_rate = cls.NSE_EXCHANGE_RATES[instrument]
        exchange_charge = (total_turnover * exch_rate).quantize(Decimal("0.01"), ROUND_HALF_UP)

        # 4. SEBI Turnover Fee
        sebi_fee = (total_turnover * cls.SEBI_FEE_RATE).quantize(Decimal("0.01"), ROUND_HALF_UP)

        # 5. Stamp Duty (Charged ONLY on Buy Side)
        if instrument == TradeInstrumentType.EQUITY_DELIVERY:
            stamp_duty = buy_turnover * Decimal("0.00015")   # 0.015%
        elif instrument in (TradeInstrumentType.EQUITY_INTRADAY, TradeInstrumentType.OPTIONS):
            stamp_duty = buy_turnover * Decimal("0.00003")   # 0.003%
        else:  # FUTURES
            stamp_duty = buy_turnover * Decimal("0.00002")   # 0.002%
        stamp_duty = stamp_duty.quantize(Decimal("1"), ROUND_HALF_UP)

        # 6. GST (18% on Brokerage + Exchange + SEBI)
        gst = ((brokerage + exchange_charge + sebi_fee) * cls.GST_RATE).quantize(Decimal("0.01"), ROUND_HALF_UP)

        total_charges = brokerage + stt + exchange_charge + sebi_fee + stamp_duty + gst
        breakeven_per_unit = (total_charges / qty).quantize(Decimal("0.05"), ROUND_HALF_UP)

        return StatutoryCostBreakdown(
            turnover=total_turnover,
            brokerage=brokerage,
            stt_ctt=stt,
            exchange_turnover_charge=exchange_charge,
            sebi_turnover_fee=sebi_fee,
            stamp_duty=stamp_duty,
            gst_18_pct=gst,
            total_charges=total_charges,
            net_breakeven_points_per_unit=breakeven_per_unit,
        )
