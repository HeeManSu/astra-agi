#!/usr/bin/env python3
"""
Run every investment-team tool with sample inputs and save results
as one Markdown file per tool-group module inside tools/tool_outputs/.

Usage:
    cd astra/runtime/examples/investment_team
    python run_all_tools.py              # default ticker: NVDA
    python run_all_tools.py AAPL         # custom ticker
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import signal
import sys
import traceback

# ── Load .env ──────────────────────────────────────────────────────────
from dotenv import load_dotenv


ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

# ── Ensure project root is on sys.path ─────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "astra" / "framework" / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

# ── Config ─────────────────────────────────────────────────────────────
TICKER = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
TOOL_TIMEOUT = 30  # seconds per tool call

OUTPUT_DIR = Path(__file__).resolve().parent / "tools" / "tool_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Timeout helper ─────────────────────────────────────────────────────
class ToolTimeout(Exception):
    pass


def _timeout_handler(signum, frame):
    raise ToolTimeout(f"Tool call exceeded {TOOL_TIMEOUT}s timeout")


# ── Helpers ────────────────────────────────────────────────────────────
def _fmt_json(raw: str) -> str:
    try:
        return json.dumps(json.loads(raw), indent=2)
    except (json.JSONDecodeError, TypeError):
        return str(raw)


def _run_tool(tool_fn, input_obj) -> tuple[str, str, bool]:
    input_repr = json.dumps(input_obj.model_dump(), indent=2, default=str)
    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(TOOL_TIMEOUT)
        result = tool_fn(input_obj)
        signal.alarm(0)

        if hasattr(result, "result"):
            output_repr = _fmt_json(result.result)
        else:
            output_repr = json.dumps(result.model_dump(), indent=2, default=str)
        return input_repr, output_repr, True
    except ToolTimeout as e:
        signal.alarm(0)
        return input_repr, f"TIMEOUT: {e}", False
    except Exception:
        signal.alarm(0)
        return input_repr, traceback.format_exc(), False


def _write_md(filename: str, title: str, entries: list[dict]) -> Path:
    path = OUTPUT_DIR / filename
    lines = [
        f"# {title}",
        "",
        f"> Generated on **{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}** "
        f"with ticker **{TICKER}**",
        "",
        "---",
        "",
    ]
    passed = sum(1 for e in entries if e["success"])
    total = len(entries)
    lines.append(f"**Results: {passed}/{total} tools succeeded**")
    lines.append("")
    lines.append("---")
    lines.append("")

    for entry in entries:
        status = "✅" if entry["success"] else "❌"
        lines.append(f"## {status} `{entry['tool']}`")
        lines.append("")
        if entry.get("description"):
            lines.append(f"_{entry['description']}_")
            lines.append("")
        lines.append("### Input")
        lines.append("")
        lines.append("```json")
        lines.append(entry["input"])
        lines.append("```")
        lines.append("")
        lines.append("### Output")
        lines.append("")
        lang = "json" if entry["success"] else "text"
        lines.append(f"```{lang}")
        lines.append(entry["output"])
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _run_group(tools_list: list[tuple]) -> list[dict]:
    entries = []
    for fn, inp, desc in tools_list:
        print(f"  → {fn.name} …", end=" ", flush=True)
        inp_s, out_s, ok = _run_tool(fn, inp)
        print("✅" if ok else "❌", flush=True)
        entries.append(
            {"tool": fn.name, "description": desc, "input": inp_s, "output": out_s, "success": ok}
        )
    return entries


# ═══════════════════════════════════════════════════════════════════════
# Tool group definitions
# ═══════════════════════════════════════════════════════════════════════


def run_macro_tools() -> Path:
    from astra.runtime.examples.investment_team.tools.macro_tools import (
        InflationGrowthInput,
        LiquidityCreditInput,
        MonetaryPolicyInput,
        get_inflation_and_growth_data,
        get_liquidity_and_credit_conditions,
        get_monetary_policy_data,
    )

    tools = [
        (
            get_monetary_policy_data,
            MonetaryPolicyInput(),
            "Fed funds rate, treasury yields, yield spread, policy stance",
        ),
        (
            get_inflation_and_growth_data,
            InflationGrowthInput(),
            "CPI, core CPI, GDP growth, unemployment rate",
        ),
        (
            get_liquidity_and_credit_conditions,
            LiquidityCreditInput(),
            "Financial conditions index, credit spread, liquidity regime",
        ),
    ]
    return _write_md("macro_tools.md", "Macro Tools", _run_group(tools))


def run_financial_tools() -> Path:
    from astra.runtime.examples.investment_team.tools.financial_tools import (
        BalanceSheetInput,
        FinancialStatementsInput,
        GrowthMetricsInput,
        KeyFinancialMetricsInput,
        get_balance_sheet_strength,
        get_financial_statements,
        get_growth_metrics,
        get_key_financial_metrics,
    )

    tools = [
        (
            get_financial_statements,
            FinancialStatementsInput(symbol=TICKER),
            "Revenue, net income, operating cashflow, EBITDA",
        ),
        (
            get_key_financial_metrics,
            KeyFinancialMetricsInput(symbol=TICKER),
            "Margins, ROE, ROA, debt-to-equity, current ratio",
        ),
        (
            get_growth_metrics,
            GrowthMetricsInput(symbol=TICKER),
            "Revenue growth, earnings growth, PEG ratio",
        ),
        (
            get_balance_sheet_strength,
            BalanceSheetInput(symbol=TICKER),
            "Total cash, debt, net cash, book value",
        ),
    ]
    return _write_md("financial_tools.md", "Financial Tools", _run_group(tools))


def run_valuation_tools() -> Path:
    from astra.runtime.examples.investment_team.tools.valuation_tools import (
        DcfInput,
        MarginOfSafetyInput,
        MarketDataInput,
        MultipleValuationInput,
        calculate_dcf,
        calculate_margin_of_safety,
        calculate_multiple_valuation,
        get_current_market_data,
    )

    tools = [
        (
            get_current_market_data,
            MarketDataInput(symbol=TICKER),
            "Price, market cap, shares outstanding, EV, FCF",
        ),
        (
            calculate_dcf,
            DcfInput(
                symbol=TICKER,
                growth_rate=0.10,
                discount_rate=0.10,
                terminal_growth=0.03,
                projection_years=5,
            ),
            "DCF fair value with bear/base/bull scenarios",
        ),
        (
            calculate_multiple_valuation,
            MultipleValuationInput(symbol=TICKER),
            "P/E, EV/EBITDA, P/B, PEG multiples",
        ),
        (
            calculate_margin_of_safety,
            MarginOfSafetyInput(current_price=150.0, fair_value=200.0),
            "Margin of safety % and buy/hold/pass verdict",
        ),
    ]
    return _write_md("valuation_tools.md", "Valuation Tools", _run_group(tools))


def run_technical_tools() -> Path:
    from astra.runtime.examples.investment_team.tools.technical_tools import (
        MacdInput,
        MovingAveragesInput,
        PriceHistoryInput,
        RsiInput,
        SupportResistanceInput,
        TrendInput,
        calculate_macd,
        calculate_moving_averages,
        calculate_rsi,
        detect_support_resistance,
        detect_trend,
        get_price_history,
    )

    tools = [
        (
            get_price_history,
            PriceHistoryInput(symbol=TICKER, days=10),
            "Recent OHLCV data (last 10 days)",
        ),
        (
            calculate_rsi,
            RsiInput(symbol=TICKER, period=14),
            "RSI value and overbought/oversold signal",
        ),
        (calculate_macd, MacdInput(symbol=TICKER), "MACD line, signal line, histogram, crossover"),
        (
            calculate_moving_averages,
            MovingAveragesInput(symbol=TICKER),
            "SMA 20/50/200, current price, trend classification",
        ),
        (detect_trend, TrendInput(symbol=TICKER), "Trend direction, strength, key levels"),
        (
            detect_support_resistance,
            SupportResistanceInput(symbol=TICKER),
            "Support and resistance levels from pivot analysis",
        ),
    ]
    return _write_md("technical_tools.md", "Technical Tools", _run_group(tools))


def run_risk_tools() -> Path:
    from astra.runtime.examples.investment_team.tools.risk_tools import (
        BetaInput,
        CorrelationInput,
        DrawdownInput,
        PortfolioStateInput,
        VolatilityInput,
        calculate_volatility,
        estimate_drawdown_risk,
        get_correlation_with_portfolio,
        get_portfolio_state,
        get_stock_beta,
    )

    tools = [
        (get_stock_beta, BetaInput(symbol=TICKER), "Beta value and risk level"),
        (
            calculate_volatility,
            VolatilityInput(symbol=TICKER),
            "Annualized volatility and regime classification",
        ),
        (
            get_correlation_with_portfolio,
            CorrelationInput(symbol=TICKER),
            "Correlation against top 5 portfolio holdings",
        ),
        (estimate_drawdown_risk, DrawdownInput(symbol=TICKER), "Max drawdown % and risk level"),
        (get_portfolio_state, PortfolioStateInput(), "Current holdings, cash, NAV, sector weights"),
    ]
    return _write_md("risk_tools.md", "Risk Tools", _run_group(tools))


def run_portfolio_tools() -> Path:
    from astra.runtime.examples.investment_team.tools.portfolio_tools import (
        CashAvailableInput,
        PortfolioBetaInput,
        PortfolioStateInput,
        SectorExposureInput,
        calculate_portfolio_beta,
        cash_available,
        get_portfolio_state,
        sector_exposure,
    )

    tools = [
        (
            get_portfolio_state,
            PortfolioStateInput(),
            "Full portfolio: holdings, cash, NAV, weights",
        ),
        (
            calculate_portfolio_beta,
            PortfolioBetaInput(),
            "Weighted portfolio beta with compliance check",
        ),
        (sector_exposure, SectorExposureInput(), "Sector weights and cap compliance"),
        (cash_available, CashAvailableInput(), "Available cash after 5% reserve"),
    ]
    return _write_md("portfolio_tools.md", "Portfolio Tools", _run_group(tools))


def run_yfinance_tools() -> Path:
    from astra.runtime.examples.investment_team.tools.yfinance_tools import (
        GetAnalystRecommendationsInput,
        GetCompanyInfoInput,
        GetCompanyNewsInput,
        GetCurrentStockPriceInput,
        GetHistoricalStockPricesInput,
        GetIncomeStatementsInput,
        GetKeyFinancialRatiosInput,
        GetStockFundamentalsInput,
        GetTechnicalIndicatorsInput,
        get_analyst_recommendations,
        get_company_info,
        get_company_news,
        get_current_stock_price,
        get_historical_stock_prices,
        get_income_statements,
        get_key_financial_ratios,
        get_stock_fundamentals,
        get_technical_indicators,
    )

    tools = [
        (get_current_stock_price, GetCurrentStockPriceInput(symbol=TICKER), "Current stock price"),
        (
            get_company_info,
            GetCompanyInfoInput(symbol=TICKER),
            "Company overview: name, sector, P/E, market cap",
        ),
        (
            get_historical_stock_prices,
            GetHistoricalStockPricesInput(symbol=TICKER, period="5d", interval="1d"),
            "Historical OHLCV (last 5 days)",
        ),
        (
            get_stock_fundamentals,
            GetStockFundamentalsInput(symbol=TICKER),
            "Fundamentals: P/E, beta, 52-week high, market cap",
        ),
        (
            get_income_statements,
            GetIncomeStatementsInput(symbol=TICKER),
            "Income statement: revenue, net income, gross profit",
        ),
        (
            get_key_financial_ratios,
            GetKeyFinancialRatiosInput(symbol=TICKER),
            "Financial ratios: P/E, P/B, ROE, debt-to-equity",
        ),
        (
            get_analyst_recommendations,
            GetAnalystRecommendationsInput(symbol=TICKER),
            "Analyst recommendations: buy/hold/sell counts",
        ),
        (
            get_company_news,
            GetCompanyNewsInput(symbol=TICKER, num_stories=3),
            "Recent company news (3 stories)",
        ),
        (
            get_technical_indicators,
            GetTechnicalIndicatorsInput(symbol=TICKER, period="1mo"),
            "Technical indicators: OHLCV with volume (1 month)",
        ),
    ]
    return _write_md("yfinance_tools.md", "YFinance Tools", _run_group(tools))


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

GROUPS = [
    ("Portfolio Tools", run_portfolio_tools),  # Local only — fastest
    ("Risk Tools", run_risk_tools),
    ("Financial Tools", run_financial_tools),
    ("Valuation Tools", run_valuation_tools),
    ("Technical Tools", run_technical_tools),
    ("YFinance Tools", run_yfinance_tools),
    ("Macro Tools", run_macro_tools),  # FRED API — slowest
]


def main():
    print(f"\n{'=' * 60}", flush=True)
    print("  Investment Team — Tool Runner", flush=True)
    print(f"  Ticker: {TICKER}  |  Timeout: {TOOL_TIMEOUT}s per tool", flush=True)
    print(f"  Output: {OUTPUT_DIR}/", flush=True)
    print(f"{'=' * 60}\n", flush=True)

    results = []
    for group_name, runner in GROUPS:
        print(f"▶ {group_name}", flush=True)
        try:
            path = runner()
            results.append((group_name, path, True))
            print(f"  ✓ Saved → {path.name}\n", flush=True)
        except Exception as e:
            print(f"  ✗ Group failed: {e}\n", flush=True)
            traceback.print_exc()
            results.append((group_name, None, False))

    print(f"\n{'=' * 60}", flush=True)
    print("  Summary", flush=True)
    print(f"{'=' * 60}", flush=True)
    for name, path, ok in results:
        status = "✅" if ok else "❌"
        loc = path.name if path else "FAILED"
        print(f"  {status} {name:20s} → {loc}", flush=True)
    print(f"\nAll output files in: {OUTPUT_DIR}/\n", flush=True)


if __name__ == "__main__":
    main()
