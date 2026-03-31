"""
Data collection module.
Fetches financial data from public APIs with full citation tracking.
"""

import json
from datetime import datetime, timezone
from typing import Optional

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _citation(source: str, url: str, detail: str = "") -> dict:
    return {"source": source, "url": url, "accessed": _now(), "detail": detail}


def fetch_all_stock_data(ticker: str) -> dict:
    """Fetch ALL available data for a ticker in one call. Returns organized dict."""
    if not HAS_YFINANCE:
        return {"error": "yfinance 未安装。运行: pip install yfinance"}
    result = {}
    try:
        t = yf.Ticker(ticker)
        info = t.info

        # Profile
        result["公司概况"] = {
            "data": {
                "公司名称": info.get("longName", "N/A"),
                "行业": info.get("industry", "N/A"),
                "板块": info.get("sector", "N/A"),
                "市值": _fmt_num(info.get("marketCap")),
                "员工数": info.get("fullTimeEmployees", "N/A"),
                "国家": info.get("country", "N/A"),
                "简介": info.get("longBusinessSummary", "N/A"),
            },
            "citation": _citation("Yahoo Finance", f"https://finance.yahoo.com/quote/{ticker}/")
        }

        # Key metrics
        result["关键财务指标"] = {
            "data": {
                "P/E (TTM)": info.get("trailingPE", "N/A"),
                "P/E (Forward)": info.get("forwardPE", "N/A"),
                "PEG": info.get("pegRatio", "N/A"),
                "P/B": info.get("priceToBook", "N/A"),
                "P/S (TTM)": info.get("priceToSalesTrailing12Months", "N/A"),
                "EV/EBITDA": info.get("enterpriseToEbitda", "N/A"),
                "EV/Revenue": info.get("enterpriseToRevenue", "N/A"),
                "毛利率": _fmt_pct(info.get("grossMargins")),
                "营业利润率": _fmt_pct(info.get("operatingMargins")),
                "净利率": _fmt_pct(info.get("profitMargins")),
                "ROE": _fmt_pct(info.get("returnOnEquity")),
                "ROA": _fmt_pct(info.get("returnOnAssets")),
                "营收增速": _fmt_pct(info.get("revenueGrowth")),
                "利润增速": _fmt_pct(info.get("earningsGrowth")),
                "Debt/Equity": info.get("debtToEquity", "N/A"),
                "流动比率": info.get("currentRatio", "N/A"),
                "总负债": _fmt_num(info.get("totalDebt")),
                "总现金": _fmt_num(info.get("totalCash")),
                "经营现金流": _fmt_num(info.get("operatingCashflow")),
                "自由现金流": _fmt_num(info.get("freeCashflow")),
            },
            "citation": _citation("Yahoo Finance", f"https://finance.yahoo.com/quote/{ticker}/key-statistics/")
        }

        # Analyst
        result["分析师预期"] = {
            "data": {
                "综合评级": info.get("recommendationKey", "N/A"),
                "分析师数量": info.get("numberOfAnalystOpinions", "N/A"),
                "目标均价": info.get("targetMeanPrice", "N/A"),
                "目标最高价": info.get("targetHighPrice", "N/A"),
                "目标最低价": info.get("targetLowPrice", "N/A"),
                "当前价格": info.get("currentPrice", "N/A"),
            },
            "citation": _citation("Yahoo Finance", f"https://finance.yahoo.com/quote/{ticker}/analysis/")
        }

        # Financial statements (simplified - top rows only)
        for name, attr, url_suffix in [
            ("利润表", "income_stmt", "financials"),
            ("资产负债表", "balance_sheet", "balance-sheet"),
            ("现金流量表", "cashflow", "cash-flow"),
        ]:
            try:
                df = getattr(t, attr, None)
                if df is not None and not df.empty:
                    table = {}
                    for col in df.columns[:4]:  # Last 4 years
                        period = str(col.date()) if hasattr(col, 'date') else str(col)
                        table[period] = {}
                        for idx in list(df.index)[:15]:  # Top 15 rows
                            val = df.loc[idx, col]
                            table[period][str(idx)] = _fmt_num(val) if val == val else "N/A"
                    result[name] = {
                        "data": table,
                        "citation": _citation("Yahoo Finance", f"https://finance.yahoo.com/quote/{ticker}/{url_suffix}/")
                    }
            except Exception:
                pass

    except Exception as e:
        result["error"] = str(e)

    return result


# ---------- Dimension-to-data mapping ----------

# Maps dimension keywords to which data sections are relevant
DIMENSION_DATA_MAP = {
    "市场规模": ["公司概况"],
    "TAM": ["公司概况"],
    "竞争格局": ["公司概况", "关键财务指标"],
    "竞争": ["公司概况", "关键财务指标"],
    "财务": ["关键财务指标", "利润表", "资产负债表", "现金流量表"],
    "指标": ["关键财务指标"],
    "利润": ["关键财务指标", "利润表"],
    "营收": ["关键财务指标", "利润表"],
    "估值": ["关键财务指标"],
    "分析师": ["分析师预期"],
    "预期": ["分析师预期"],
    "现金流": ["关键财务指标", "现金流量表"],
    "资产负债": ["资产负债表", "关键财务指标"],
    "杠杆": ["关键财务指标", "资产负债表"],
    "增长": ["关键财务指标", "利润表"],
    "盈利": ["关键财务指标", "利润表"],
    "概况": ["公司概况"],
}


def get_relevant_data_for_dimension(dim: str, all_data: dict) -> dict:
    """Given a dimension name and all fetched data, return the relevant subset."""
    relevant = {}

    # Check which data sections match this dimension
    dim_lower = dim.lower()
    matched_sections = set()

    for keyword, sections in DIMENSION_DATA_MAP.items():
        if keyword in dim_lower or keyword in dim:
            matched_sections.update(sections)

    # If no keyword match, return ALL financial data (better to show more than nothing)
    if not matched_sections:
        matched_sections = {"公司概况", "关键财务指标"}

    for section in matched_sections:
        if section in all_data:
            relevant[section] = all_data[section]

    return relevant


def check_dependencies() -> dict:
    return {
        "yfinance": HAS_YFINANCE,
        "requests": HAS_REQUESTS,
    }


# ---------- Yahoo Finance ----------

def fetch_profile(ticker: str) -> dict:
    """Company profile: name, sector, market cap, description."""
    if not HAS_YFINANCE:
        return {"error": "yfinance 未安装。运行: pip install yfinance"}
    try:
        t = yf.Ticker(ticker)
        info = t.info
        data = {
            "公司名称": info.get("longName", "N/A"),
            "行业": info.get("industry", "N/A"),
            "板块": info.get("sector", "N/A"),
            "市值": info.get("marketCap", "N/A"),
            "货币": info.get("currency", "USD"),
            "交易所": info.get("exchange", "N/A"),
            "员工数": info.get("fullTimeEmployees", "N/A"),
            "国家": info.get("country", "N/A"),
            "简介": info.get("longBusinessSummary", "N/A"),
        }
        return {
            "data": data,
            "citation": _citation("Yahoo Finance",
                                  f"https://finance.yahoo.com/quote/{ticker}/",
                                  f"{ticker} 公司概况")
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_key_metrics(ticker: str) -> dict:
    """Key financial metrics: valuation, profitability, growth, leverage."""
    if not HAS_YFINANCE:
        return {"error": "yfinance 未安装"}
    try:
        t = yf.Ticker(ticker)
        info = t.info
        data = {
            "估值": {
                "P/E (TTM)": info.get("trailingPE", "N/A"),
                "P/E (Forward)": info.get("forwardPE", "N/A"),
                "PEG": info.get("pegRatio", "N/A"),
                "P/B": info.get("priceToBook", "N/A"),
                "P/S (TTM)": info.get("priceToSalesTrailing12Months", "N/A"),
                "EV/EBITDA": info.get("enterpriseToEbitda", "N/A"),
                "EV/Revenue": info.get("enterpriseToRevenue", "N/A"),
            },
            "盈利能力": {
                "毛利率": _fmt_pct(info.get("grossMargins")),
                "营业利润率": _fmt_pct(info.get("operatingMargins")),
                "净利率": _fmt_pct(info.get("profitMargins")),
                "ROE": _fmt_pct(info.get("returnOnEquity")),
                "ROA": _fmt_pct(info.get("returnOnAssets")),
            },
            "增长": {
                "营收增速": _fmt_pct(info.get("revenueGrowth")),
                "利润增速": _fmt_pct(info.get("earningsGrowth")),
            },
            "资产负债": {
                "Debt/Equity": info.get("debtToEquity", "N/A"),
                "流动比率": info.get("currentRatio", "N/A"),
                "总负债": _fmt_num(info.get("totalDebt")),
                "总现金": _fmt_num(info.get("totalCash")),
            },
            "现金流": {
                "经营现金流": _fmt_num(info.get("operatingCashflow")),
                "自由现金流": _fmt_num(info.get("freeCashflow")),
            }
        }
        return {
            "data": data,
            "citation": _citation("Yahoo Finance",
                                  f"https://finance.yahoo.com/quote/{ticker}/key-statistics/",
                                  f"{ticker} 关键指标")
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_financials(ticker: str) -> dict:
    """Income statement, balance sheet, cash flow (annual)."""
    if not HAS_YFINANCE:
        return {"error": "yfinance 未安装"}
    try:
        t = yf.Ticker(ticker)
        result = {}

        for name, attr, url_suffix in [
            ("利润表", "income_stmt", "financials"),
            ("资产负债表", "balance_sheet", "balance-sheet"),
            ("现金流量表", "cashflow", "cash-flow"),
        ]:
            df = getattr(t, attr, None)
            if df is not None and not df.empty:
                # Convert to simple dict with string keys
                table = {}
                for col in df.columns:
                    period = str(col.date()) if hasattr(col, 'date') else str(col)
                    table[period] = {}
                    for idx in df.index:
                        val = df.loc[idx, col]
                        table[period][str(idx)] = _fmt_num(val) if val == val else "N/A"
                result[name] = {
                    "data": table,
                    "periods": list(table.keys()),
                    "citation": _citation("Yahoo Finance",
                                          f"https://finance.yahoo.com/quote/{ticker}/{url_suffix}/",
                                          f"{ticker} {name}")
                }
            else:
                result[name] = {"data": {}, "note": "数据不可用"}

        return result
    except Exception as e:
        return {"error": str(e)}


def fetch_analyst(ticker: str) -> dict:
    """Analyst estimates and price targets."""
    if not HAS_YFINANCE:
        return {"error": "yfinance 未安装"}
    try:
        t = yf.Ticker(ticker)
        info = t.info
        data = {
            "综合评级": info.get("recommendationKey", "N/A"),
            "分析师数量": info.get("numberOfAnalystOpinions", "N/A"),
            "目标均价": info.get("targetMeanPrice", "N/A"),
            "目标最高价": info.get("targetHighPrice", "N/A"),
            "目标最低价": info.get("targetLowPrice", "N/A"),
            "当前价格": info.get("currentPrice", "N/A"),
        }
        return {
            "data": data,
            "citation": _citation("Yahoo Finance",
                                  f"https://finance.yahoo.com/quote/{ticker}/analysis/",
                                  f"{ticker} 分析师预期")
        }
    except Exception as e:
        return {"error": str(e)}


# ---------- Helpers ----------

def _fmt_pct(val) -> str:
    if val is None or val == "N/A":
        return "N/A"
    try:
        return f"{float(val) * 100:.1f}%"
    except (ValueError, TypeError):
        return str(val)


def _fmt_num(val) -> str:
    if val is None or val == "N/A":
        return "N/A"
    try:
        v = float(val)
        if abs(v) >= 1e12:
            return f"${v/1e12:.2f}T"
        if abs(v) >= 1e9:
            return f"${v/1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"${v/1e6:.1f}M"
        return f"${v:,.0f}"
    except (ValueError, TypeError):
        return str(val)


def search_web(query: str, max_results: int = 8) -> list:
    """
    Search the web using DuckDuckGo (free, no API key needed).
    Returns a list of {title, url, snippet} dicts.
    """
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                }
                for r in results
            ]
    except ImportError:
        return [{"title": "[duckduckgo_search 未安装]", "url": "", "snippet": "pip install duckduckgo_search"}]
    except Exception as e:
        return [{"title": f"[搜索出错: {e}]", "url": "", "snippet": ""}]


def search_news(query: str, max_results: int = 6) -> list:
    """Search recent news using DuckDuckGo News."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", r.get("link", "")),
                    "snippet": r.get("body", ""),
                    "date": r.get("date", ""),
                    "source": r.get("source", ""),
                }
                for r in results
            ]
    except Exception as e:
        return [{"title": f"[新闻搜索出错: {e}]", "url": "", "snippet": ""}]


def build_search_queries(topic: str, dimension: str, ticker: str = "") -> list:
    """Generate multiple targeted search queries for a given dimension."""
    queries = []
    base = topic

    # Dimension-specific query templates
    dim_lower = dimension.lower()

    if any(k in dim_lower for k in ["市场规模", "tam", "market size"]):
        queries.append(f"{base} total addressable market size 2025 2026")
        queries.append(f"{base} market size forecast growth rate")
        if ticker:
            queries.append(f"{ticker} TAM addressable market investor presentation")

    elif any(k in dim_lower for k in ["竞争", "competitive", "competition"]):
        queries.append(f"{base} competitive landscape market share")
        queries.append(f"{base} competitors comparison 2025")
        if ticker:
            queries.append(f"{ticker} vs competitors market share")

    elif any(k in dim_lower for k in ["营收", "revenue", "收入"]):
        queries.append(f"{base} revenue breakdown by segment")
        if ticker:
            queries.append(f"{ticker} revenue breakdown segment quarterly")
            queries.append(f"{ticker} 10-K annual report revenue")

    elif any(k in dim_lower for k in ["财务", "financial", "指标", "metrics"]):
        if ticker:
            queries.append(f"{ticker} key financial metrics 2025")
            queries.append(f"{ticker} earnings results latest quarter")

    elif any(k in dim_lower for k in ["供应链", "supply chain"]):
        queries.append(f"{base} supply chain analysis key suppliers")
        queries.append(f"{base} supply chain risks dependencies")

    elif any(k in dim_lower for k in ["监管", "regulatory", "政策", "policy"]):
        queries.append(f"{base} regulatory risks policy changes 2025")
        queries.append(f"{base} government regulation impact")

    elif any(k in dim_lower for k in ["分析师", "analyst", "预期", "estimate"]):
        if ticker:
            queries.append(f"{ticker} analyst estimates price target 2025")
            queries.append(f"{ticker} earnings estimates consensus")

    elif any(k in dim_lower for k in ["管理层", "management"]):
        if ticker:
            queries.append(f"{ticker} CEO management commentary latest")
            queries.append(f"{ticker} earnings call transcript highlights")

    elif any(k in dim_lower for k in ["风险", "risk"]):
        queries.append(f"{base} investment risks analysis")
        if ticker:
            queries.append(f"{ticker} risk factors 10-K")

    elif any(k in dim_lower for k in ["催化剂", "catalyst"]):
        queries.append(f"{base} upcoming catalysts near term")
        if ticker:
            queries.append(f"{ticker} catalysts growth drivers 2025 2026")

    elif any(k in dim_lower for k in ["估值", "valuation"]):
        if ticker:
            queries.append(f"{ticker} valuation analysis fair value")
            queries.append(f"{ticker} PE ratio EV/EBITDA compared to peers")

    # Always add a general query if we have fewer than 2
    if len(queries) < 2:
        queries.append(f"{base} {dimension} analysis 2025")
        queries.append(f"{base} {dimension} data")

    return queries[:4]  # Max 4 queries per dimension


def research_dimension(topic: str, dimension: str, ticker: str = "",
                       all_stock_data: dict = None) -> dict:
    """
    Comprehensive data collection for a single dimension.
    Combines: financial data (yfinance) + web search + news search.
    Returns structured result with all citations.
    """
    result = {
        "dimension": dimension,
        "financial_data": {},
        "web_results": [],
        "news_results": [],
        "search_queries_used": [],
        "citations": [],
    }

    # 1. Financial data (from pre-fetched stock data)
    if all_stock_data:
        relevant = get_relevant_data_for_dimension(dimension, all_stock_data)
        if relevant:
            result["financial_data"] = relevant
            for section_name, section_data in relevant.items():
                if "citation" in section_data:
                    result["citations"].append(section_data["citation"])

    # 2. Web search
    queries = build_search_queries(topic, dimension, ticker)
    result["search_queries_used"] = queries

    all_web = []
    seen_urls = set()
    for q in queries:
        web_results = search_web(q, max_results=5)
        for r in web_results:
            if r["url"] and r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_web.append(r)
                result["citations"].append(_citation(
                    r.get("title", "Web"),
                    r["url"],
                    r.get("snippet", "")[:100]
                ))
    result["web_results"] = all_web[:10]  # Top 10 unique results

    # 3. News search
    news_query = f"{topic} {dimension}" if not ticker else f"{ticker} {dimension}"
    news_results = search_news(news_query, max_results=5)
    result["news_results"] = [n for n in news_results if n.get("url")]
    for n in result["news_results"]:
        result["citations"].append(_citation(
            n.get("source", n.get("title", "News")),
            n.get("url", ""),
            n.get("title", "")
        ))

    return result
