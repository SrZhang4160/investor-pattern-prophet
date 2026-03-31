#!/usr/bin/env python3
"""
Financial data fetching utilities for the Investment Research Agent.
Fetches data from public APIs with full citation tracking.

Usage:
  python fetch_financial_data.py --ticker NVDA --type financials
  python fetch_financial_data.py --ticker NVDA --type profile
  python fetch_financial_data.py --ticker NVDA --type estimates
  python fetch_financial_data.py --fred-series GDP --start 2020-01-01
  python fetch_financial_data.py --ticker NVDA --type all

Output: JSON with data + citations
"""

import json
import sys
import os
from datetime import datetime, timezone

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False


def get_timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def make_citation(source_name, url, detail=""):
    return {
        "source": source_name,
        "url": url,
        "accessed": get_timestamp(),
        "detail": detail
    }


def fetch_company_profile(ticker_symbol):
    """Fetch basic company info."""
    if not HAS_YFINANCE:
        return {"error": "yfinance not installed. Run: pip install yfinance"}

    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info

    profile = {
        "name": info.get("longName", "N/A"),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "market_cap": info.get("marketCap", "N/A"),
        "currency": info.get("currency", "USD"),
        "exchange": info.get("exchange", "N/A"),
        "website": info.get("website", "N/A"),
        "employees": info.get("fullTimeEmployees", "N/A"),
        "description": info.get("longBusinessSummary", "N/A"),
        "country": info.get("country", "N/A"),
    }

    citation = make_citation(
        "Yahoo Finance",
        f"https://finance.yahoo.com/quote/{ticker_symbol}/",
        f"Company profile for {ticker_symbol}"
    )

    return {"data": profile, "citation": citation}


def fetch_financials(ticker_symbol):
    """Fetch income statement, balance sheet, cash flow."""
    if not HAS_YFINANCE:
        return {"error": "yfinance not installed. Run: pip install yfinance"}

    ticker = yf.Ticker(ticker_symbol)
    result = {}

    # Income statement
    try:
        income = ticker.income_stmt
        if income is not None and not income.empty:
            result["income_statement"] = {
                "data": income.to_dict(),
                "periods": [str(col.date()) if hasattr(col, 'date') else str(col) for col in income.columns],
                "citation": make_citation(
                    "Yahoo Finance",
                    f"https://finance.yahoo.com/quote/{ticker_symbol}/financials/",
                    "Annual income statement"
                )
            }
    except Exception as e:
        result["income_statement"] = {"error": str(e)}

    # Balance sheet
    try:
        balance = ticker.balance_sheet
        if balance is not None and not balance.empty:
            result["balance_sheet"] = {
                "data": balance.to_dict(),
                "periods": [str(col.date()) if hasattr(col, 'date') else str(col) for col in balance.columns],
                "citation": make_citation(
                    "Yahoo Finance",
                    f"https://finance.yahoo.com/quote/{ticker_symbol}/balance-sheet/",
                    "Annual balance sheet"
                )
            }
    except Exception as e:
        result["balance_sheet"] = {"error": str(e)}

    # Cash flow
    try:
        cashflow = ticker.cashflow
        if cashflow is not None and not cashflow.empty:
            result["cash_flow"] = {
                "data": cashflow.to_dict(),
                "periods": [str(col.date()) if hasattr(col, 'date') else str(col) for col in cashflow.columns],
                "citation": make_citation(
                    "Yahoo Finance",
                    f"https://finance.yahoo.com/quote/{ticker_symbol}/cash-flow/",
                    "Annual cash flow statement"
                )
            }
    except Exception as e:
        result["cash_flow"] = {"error": str(e)}

    return result


def fetch_key_metrics(ticker_symbol):
    """Fetch key valuation and financial metrics."""
    if not HAS_YFINANCE:
        return {"error": "yfinance not installed. Run: pip install yfinance"}

    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info

    metrics = {
        "valuation": {
            "pe_ratio_ttm": info.get("trailingPE", "N/A"),
            "pe_ratio_forward": info.get("forwardPE", "N/A"),
            "peg_ratio": info.get("pegRatio", "N/A"),
            "price_to_book": info.get("priceToBook", "N/A"),
            "price_to_sales_ttm": info.get("priceToSalesTrailing12Months", "N/A"),
            "ev_to_ebitda": info.get("enterpriseToEbitda", "N/A"),
            "ev_to_revenue": info.get("enterpriseToRevenue", "N/A"),
        },
        "profitability": {
            "gross_margin": info.get("grossMargins", "N/A"),
            "operating_margin": info.get("operatingMargins", "N/A"),
            "net_margin": info.get("profitMargins", "N/A"),
            "roe": info.get("returnOnEquity", "N/A"),
            "roa": info.get("returnOnAssets", "N/A"),
        },
        "growth": {
            "revenue_growth": info.get("revenueGrowth", "N/A"),
            "earnings_growth": info.get("earningsGrowth", "N/A"),
        },
        "balance_sheet_health": {
            "debt_to_equity": info.get("debtToEquity", "N/A"),
            "current_ratio": info.get("currentRatio", "N/A"),
            "total_debt": info.get("totalDebt", "N/A"),
            "total_cash": info.get("totalCash", "N/A"),
        },
        "cash_flow": {
            "operating_cf": info.get("operatingCashflow", "N/A"),
            "free_cf": info.get("freeCashflow", "N/A"),
        },
        "dividends": {
            "dividend_yield": info.get("dividendYield", "N/A"),
            "payout_ratio": info.get("payoutRatio", "N/A"),
        }
    }

    citation = make_citation(
        "Yahoo Finance",
        f"https://finance.yahoo.com/quote/{ticker_symbol}/key-statistics/",
        f"Key statistics for {ticker_symbol}"
    )

    return {"data": metrics, "citation": citation}


def fetch_analyst_estimates(ticker_symbol):
    """Fetch analyst recommendations and price targets."""
    if not HAS_YFINANCE:
        return {"error": "yfinance not installed. Run: pip install yfinance"}

    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info

    estimates = {
        "recommendation": info.get("recommendationKey", "N/A"),
        "num_analysts": info.get("numberOfAnalystOpinions", "N/A"),
        "target_mean_price": info.get("targetMeanPrice", "N/A"),
        "target_high_price": info.get("targetHighPrice", "N/A"),
        "target_low_price": info.get("targetLowPrice", "N/A"),
        "target_median_price": info.get("targetMedianPrice", "N/A"),
        "current_price": info.get("currentPrice", "N/A"),
    }

    # Try to get recommendation trends
    try:
        recs = ticker.recommendations
        if recs is not None and not recs.empty:
            recent = recs.tail(5).to_dict(orient='records')
            estimates["recent_recommendations"] = recent
    except Exception:
        pass

    citation = make_citation(
        "Yahoo Finance",
        f"https://finance.yahoo.com/quote/{ticker_symbol}/analysis/",
        f"Analyst estimates for {ticker_symbol}"
    )

    return {"data": estimates, "citation": citation}


def fetch_fred_data(series_id, start_date=None, end_date=None):
    """Fetch macroeconomic data from FRED.
    Note: Requires FRED API key set as FRED_API_KEY environment variable.
    If not available, provides the FRED URL for manual lookup."""

    api_key = os.environ.get("FRED_API_KEY")

    if not api_key:
        return {
            "data": None,
            "manual_lookup": f"https://fred.stlouisfed.org/series/{series_id}",
            "citation": make_citation(
                "FRED (Federal Reserve Economic Data)",
                f"https://fred.stlouisfed.org/series/{series_id}",
                f"Series: {series_id}"
            ),
            "note": "FRED API key not configured. Use the URL above for manual data lookup, or set FRED_API_KEY environment variable."
        }

    try:
        import requests
        params = {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json"
        }
        if start_date:
            params["observation_start"] = start_date
        if end_date:
            params["observation_end"] = end_date

        resp = requests.get("https://api.stlouisfed.org/fred/series/observations", params=params)
        data = resp.json()

        return {
            "data": data.get("observations", []),
            "citation": make_citation(
                "FRED (Federal Reserve Economic Data)",
                f"https://fred.stlouisfed.org/series/{series_id}",
                f"Series: {series_id}, retrieved via API"
            )
        }
    except Exception as e:
        return {"error": str(e)}


def format_output(result):
    """Convert all data to JSON-serializable format."""

    def convert(obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        if hasattr(obj, 'item'):  # numpy types
            return obj.item()
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert(i) for i in obj]
        return obj

    return convert(result)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fetch financial data with citations")
    parser.add_argument("--ticker", help="Stock ticker symbol (e.g., NVDA)")
    parser.add_argument("--type", choices=["profile", "financials", "metrics", "estimates", "all"],
                        default="all", help="Type of data to fetch")
    parser.add_argument("--fred-series", help="FRED series ID (e.g., GDP, DFF, CPIAUCSL)")
    parser.add_argument("--start", help="Start date for FRED data (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date for FRED data (YYYY-MM-DD)")
    parser.add_argument("--output", help="Output file path (default: stdout)")

    args = parser.parse_args()

    result = {}

    if args.fred_series:
        result["fred"] = fetch_fred_data(args.fred_series, args.start, args.end)
    elif args.ticker:
        ticker = args.ticker.upper()
        if args.type in ("profile", "all"):
            result["profile"] = fetch_company_profile(ticker)
        if args.type in ("financials", "all"):
            result["financials"] = fetch_financials(ticker)
        if args.type in ("metrics", "all"):
            result["key_metrics"] = fetch_key_metrics(ticker)
        if args.type in ("estimates", "all"):
            result["analyst_estimates"] = fetch_analyst_estimates(ticker)
    else:
        parser.print_help()
        sys.exit(1)

    result = format_output(result)
    output = json.dumps(result, indent=2, ensure_ascii=False, default=str)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"✅ Data saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
