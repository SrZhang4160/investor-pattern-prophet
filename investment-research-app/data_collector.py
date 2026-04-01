"""
Data collection module.
Fetches financial data from public APIs with full citation tracking.
Multiple search engines: DuckDuckGo, Google (via DDGS), Brave, SEC EDGAR.
"""

import json
import os
import re
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
                "股息率": _fmt_pct(info.get("dividendYield")),
                "Beta": info.get("beta", "N/A"),
                "52周最高": info.get("fiftyTwoWeekHigh", "N/A"),
                "52周最低": info.get("fiftyTwoWeekLow", "N/A"),
                "Shares Outstanding": _fmt_num(info.get("sharesOutstanding")),
                "Float": _fmt_num(info.get("floatShares")),
                "内部人持股": _fmt_pct(info.get("heldPercentInsiders")),
                "机构持股": _fmt_pct(info.get("heldPercentInstitutions")),
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

        # Quarterly financials
        for name, attr, url_suffix in [
            ("季度利润表", "quarterly_income_stmt", "financials"),
            ("季度现金流量表", "quarterly_cashflow", "cash-flow"),
        ]:
            try:
                df = getattr(t, attr, None)
                if df is not None and not df.empty:
                    table = {}
                    for col in df.columns[:4]:
                        period = str(col.date()) if hasattr(col, 'date') else str(col)
                        table[period] = {}
                        for idx in list(df.index)[:10]:
                            val = df.loc[idx, col]
                            table[period][str(idx)] = _fmt_num(val) if val == val else "N/A"
                    result[name] = {
                        "data": table,
                        "citation": _citation("Yahoo Finance", f"https://finance.yahoo.com/quote/{ticker}/{url_suffix}/")
                    }
            except Exception:
                pass

        # Insider & institutional holders
        try:
            inst = t.institutional_holders
            if inst is not None and not inst.empty:
                holders = []
                for _, row in inst.head(10).iterrows():
                    holders.append({
                        "持有者": str(row.get("Holder", "N/A")),
                        "持股数": _fmt_num(row.get("Shares", 0)),
                        "比例": _fmt_pct(row.get("pctHeld", row.get("% Out", None))),
                    })
                result["机构持股明细"] = {
                    "data": holders,
                    "citation": _citation("Yahoo Finance", f"https://finance.yahoo.com/quote/{ticker}/holders/")
                }
        except Exception:
            pass

    except Exception as e:
        result["error"] = str(e)

    return result


# ---------- Dimension-to-data mapping ----------

DIMENSION_DATA_MAP = {
    "市场规模": ["公司概况"],
    "TAM": ["公司概况"],
    "竞争格局": ["公司概况", "关键财务指标"],
    "竞争": ["公司概况", "关键财务指标"],
    "财务": ["关键财务指标", "利润表", "资产负债表", "现金流量表"],
    "指标": ["关键财务指标"],
    "利润": ["关键财务指标", "利润表", "季度利润表"],
    "营收": ["关键财务指标", "利润表", "季度利润表"],
    "估值": ["关键财务指标", "分析师预期"],
    "分析师": ["分析师预期"],
    "预期": ["分析师预期"],
    "现金流": ["关键财务指标", "现金流量表", "季度现金流量表"],
    "资产负债": ["资产负债表", "关键财务指标"],
    "杠杆": ["关键财务指标", "资产负债表"],
    "增长": ["关键财务指标", "利润表", "季度利润表"],
    "盈利": ["关键财务指标", "利润表"],
    "概况": ["公司概况"],
    "持股": ["关键财务指标", "机构持股明细"],
    "机构": ["机构持股明细"],
    "股东": ["机构持股明细"],
    "季度": ["季度利润表", "季度现金流量表"],
}


def get_relevant_data_for_dimension(dim: str, all_data: dict) -> dict:
    """Given a dimension name and all fetched data, return the relevant subset."""
    relevant = {}
    dim_lower = dim.lower()
    matched_sections = set()

    for keyword, sections in DIMENSION_DATA_MAP.items():
        if keyword in dim_lower or keyword in dim:
            matched_sections.update(sections)

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


# ============================================================
#  SEARCH ENGINES
# ============================================================

def search_web(query: str, max_results: int = 8) -> list:
    """Search the web using DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                    "engine": "DuckDuckGo",
                }
                for r in results
            ]
    except ImportError:
        return [{"title": "[duckduckgo_search 未安装]", "url": "", "snippet": "pip install duckduckgo_search", "engine": ""}]
    except Exception as e:
        return [{"title": f"[DuckDuckGo 搜索出错: {e}]", "url": "", "snippet": "", "engine": ""}]


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
                    "engine": "DuckDuckGo News",
                }
                for r in results
            ]
    except Exception as e:
        return [{"title": f"[新闻搜索出错: {e}]", "url": "", "snippet": "", "engine": ""}]


def search_brave(query: str, max_results: int = 8) -> list:
    """Search using Brave Search API (requires BRAVE_API_KEY)."""
    if not HAS_REQUESTS:
        return []
    api_key = _get_env("BRAVE_API_KEY")
    if not api_key:
        return []  # Silently skip if not configured
    try:
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            params={"q": query, "count": max_results},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("description", ""),
                    "engine": "Brave Search",
                }
                for r in data.get("web", {}).get("results", [])
            ]
    except Exception:
        pass
    return []


def search_google_via_serp(query: str, max_results: int = 8) -> list:
    """Search Google via SerpAPI (requires SERPAPI_KEY)."""
    if not HAS_REQUESTS:
        return []
    api_key = _get_env("SERPAPI_KEY")
    if not api_key:
        return []
    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={"q": query, "num": max_results, "api_key": api_key, "engine": "google"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "snippet": r.get("snippet", ""),
                    "engine": "Google (SerpAPI)",
                }
                for r in data.get("organic_results", [])
            ]
    except Exception:
        pass
    return []


def search_sec_edgar(ticker: str, filing_type: str = "10-K", max_results: int = 5) -> list:
    """Search SEC EDGAR for company filings."""
    if not HAS_REQUESTS or not ticker:
        return []
    try:
        # Step 1: Look up CIK from ticker
        headers = {"User-Agent": "InvestmentResearchAgent/1.0 (research@example.com)"}
        resp = requests.get(
            f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2024-01-01&forms={filing_type}",
            headers=headers, timeout=10
        )
        # Use EDGAR full-text search
        search_url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms={filing_type}&dateRange=custom&startdt=2023-01-01"
        resp2 = requests.get(
            f"https://efts.sec.gov/LATEST/search-index?q={ticker}&forms={filing_type}",
            headers=headers, timeout=10
        )

        # Simpler approach: use EDGAR company search
        resp3 = requests.get(
            f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=&CIK={ticker}&type={filing_type}&dateb=&owner=include&count={max_results}&search_text=&action=getcompany",
            headers=headers, timeout=10
        )

        # Use EDGAR XBRL API (more reliable)
        resp4 = requests.get(
            f"https://efts.sec.gov/LATEST/search-index?q={ticker}&forms={filing_type}&dateRange=custom&startdt=2023-01-01",
            headers=headers, timeout=10
        )

        # Use the EDGAR full-text search API
        search_resp = requests.get(
            f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms={filing_type}",
            headers=headers, timeout=10
        )

        # Best approach: EDGAR full-text search
        edgar_results = []
        search_api = f"https://efts.sec.gov/LATEST/search-index?q={ticker}&forms={filing_type}&dateRange=custom&startdt=2023-01-01"
        r = requests.get(search_api, headers=headers, timeout=10)
        if r.status_code == 200:
            hits = r.json().get("hits", {}).get("hits", [])
            for hit in hits[:max_results]:
                src = hit.get("_source", {})
                edgar_results.append({
                    "title": f"{src.get('display_names', [ticker])[0]} - {filing_type} ({src.get('file_date', 'N/A')})",
                    "url": f"https://www.sec.gov/Archives/edgar/data/{src.get('entity_id', '')}/{src.get('file_num', '')}",
                    "snippet": src.get("display_names", [""])[0],
                    "engine": "SEC EDGAR",
                })
            if edgar_results:
                return edgar_results

        # Fallback: just provide direct link
        return [{
            "title": f"{ticker} SEC Filings ({filing_type})",
            "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type={filing_type}&dateb=&owner=include&count=10&search_text=&action=getcompany",
            "snippet": f"SEC EDGAR filings for {ticker}",
            "engine": "SEC EDGAR",
        }]
    except Exception:
        return [{
            "title": f"{ticker} SEC Filings",
            "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type={filing_type}&dateb=&owner=include&count=10",
            "snippet": f"SEC EDGAR filings for {ticker}",
            "engine": "SEC EDGAR",
        }]


def _get_env(key: str) -> str:
    """Get an env var, falling back to .env file."""
    val = os.environ.get(key, "").strip()
    if val:
        return val
    env_paths = [".env", os.path.join(os.path.dirname(__file__), ".env")]
    for path in env_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith(key + "="):
                            return line.split("=", 1)[1].strip().strip("'\"")
            except Exception:
                pass
    return ""


def multi_engine_search(query: str, max_per_engine: int = 6) -> list:
    """Search across all available engines, deduplicate by URL."""
    all_results = []
    seen_urls = set()

    # DuckDuckGo (always available, no API key)
    for r in search_web(query, max_results=max_per_engine):
        if r.get("url") and r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            all_results.append(r)

    # Brave (if configured)
    for r in search_brave(query, max_results=max_per_engine):
        if r.get("url") and r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            all_results.append(r)

    # Google/SerpAPI (if configured)
    for r in search_google_via_serp(query, max_results=max_per_engine):
        if r.get("url") and r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            all_results.append(r)

    return all_results


# ============================================================
#  QUERY BUILDERS
# ============================================================

def build_search_queries(topic: str, dimension: str, ticker: str = "") -> list:
    """Generate multiple targeted search queries for a given dimension."""
    queries = []
    base = topic
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

    elif any(k in dim_lower for k in ["esg", "环境", "社会"]):
        queries.append(f"{base} ESG rating sustainability report")
        if ticker:
            queries.append(f"{ticker} ESG score environmental social governance")

    elif any(k in dim_lower for k in ["持股", "insider", "机构", "institutional"]):
        if ticker:
            queries.append(f"{ticker} insider buying selling transactions")
            queries.append(f"{ticker} institutional ownership changes")

    # Always add a general query if we have fewer than 2
    if len(queries) < 2:
        queries.append(f"{base} {dimension} analysis 2025")
        queries.append(f"{base} {dimension} data")

    return queries[:4]


def build_refinement_queries(topic: str, dimension: str, feedback: str,
                              ticker: str = "") -> list:
    """Build NEW search queries based on trainer feedback about missing/insufficient data."""
    queries = []
    base = topic

    # Parse feedback for keywords — the feedback is natural language from the trainer
    # Examples: "需要更多关于供应商的数据", "缺少季度数据", "想看同比增长"
    feedback_lower = feedback.lower()

    # Direct query from feedback
    queries.append(f"{base} {feedback}")

    # If ticker, add ticker-specific version
    if ticker:
        queries.append(f"{ticker} {feedback}")

    # Add more specific queries based on common patterns in feedback
    if any(k in feedback_lower for k in ["更多", "更详细", "深入", "细化"]):
        queries.append(f"{base} {dimension} detailed analysis report")
    if any(k in feedback_lower for k in ["对比", "比较", "vs", "同行"]):
        queries.append(f"{base} {dimension} peer comparison benchmark")
    if any(k in feedback_lower for k in ["历史", "趋势", "变化"]):
        queries.append(f"{base} {dimension} historical trend 5 year")
    if any(k in feedback_lower for k in ["最新", "近期", "recent"]):
        queries.append(f"{base} {dimension} latest 2025")
    if any(k in feedback_lower for k in ["来源", "source", "报告", "report"]):
        queries.append(f"{base} {dimension} research report PDF")

    return queries[:5]


# ============================================================
#  MAIN RESEARCH FUNCTIONS
# ============================================================

def research_dimension(topic: str, dimension: str, ticker: str = "",
                       all_stock_data: dict = None) -> dict:
    """
    Comprehensive data collection for a single dimension.
    Combines: financial data (yfinance) + multi-engine web search + news + SEC.
    """
    result = {
        "dimension": dimension,
        "financial_data": {},
        "web_results": [],
        "news_results": [],
        "sec_results": [],
        "search_queries_used": [],
        "citations": [],
        "refinement_rounds": [],
    }

    # 1. Financial data (from pre-fetched stock data)
    if all_stock_data:
        relevant = get_relevant_data_for_dimension(dimension, all_stock_data)
        if relevant:
            result["financial_data"] = relevant
            for section_name, section_data in relevant.items():
                if "citation" in section_data:
                    result["citations"].append(section_data["citation"])

    # 2. Multi-engine web search
    queries = build_search_queries(topic, dimension, ticker)
    result["search_queries_used"] = queries

    all_web = []
    seen_urls = set()
    for q in queries:
        web_results = multi_engine_search(q, max_per_engine=5)
        for r in web_results:
            if r["url"] and r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_web.append(r)
                result["citations"].append(_citation(
                    r.get("title", "Web"),
                    r["url"],
                    r.get("snippet", "")[:100]
                ))
    result["web_results"] = all_web[:15]  # Top 15 unique results

    # 3. News search
    news_query = f"{topic} {dimension}" if not ticker else f"{ticker} {dimension}"
    news_results = search_news(news_query, max_results=6)
    result["news_results"] = [n for n in news_results if n.get("url")]
    for n in result["news_results"]:
        result["citations"].append(_citation(
            n.get("source", n.get("title", "News")),
            n.get("url", ""),
            n.get("title", "")
        ))

    # 4. SEC EDGAR (if ticker provided)
    if ticker:
        sec_results = search_sec_edgar(ticker, "10-K", max_results=3)
        sec_results += search_sec_edgar(ticker, "10-Q", max_results=2)
        result["sec_results"] = sec_results
        for s in sec_results:
            if s.get("url"):
                result["citations"].append(_citation(s.get("title", "SEC"), s["url"], "SEC Filing"))

    return result


def refine_dimension(existing_result: dict, feedback: str, topic: str,
                     dimension: str, ticker: str = "",
                     all_stock_data: dict = None) -> dict:
    """
    Based on trainer feedback, do additional targeted searches and merge
    into the existing result. Returns the updated result dict.
    """
    new_queries = build_refinement_queries(topic, dimension, feedback, ticker)
    round_data = {
        "feedback": feedback,
        "new_queries": new_queries,
        "new_web_results": [],
        "new_news_results": [],
    }

    seen_urls = set()
    for r in existing_result.get("web_results", []):
        if r.get("url"):
            seen_urls.add(r["url"])
    for r in existing_result.get("news_results", []):
        if r.get("url"):
            seen_urls.add(r["url"])

    # Additional web search with new queries
    for q in new_queries:
        web_results = multi_engine_search(q, max_per_engine=5)
        for r in web_results:
            if r.get("url") and r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                existing_result["web_results"].append(r)
                round_data["new_web_results"].append(r)
                existing_result["citations"].append(_citation(
                    r.get("title", "Web"),
                    r["url"],
                    r.get("snippet", "")[:100]
                ))

    # Additional news
    news_query = f"{topic} {feedback}"
    news_results = search_news(news_query, max_results=4)
    for n in news_results:
        if n.get("url") and n["url"] not in seen_urls:
            seen_urls.add(n["url"])
            existing_result["news_results"].append(n)
            round_data["new_news_results"].append(n)
            existing_result["citations"].append(_citation(
                n.get("source", n.get("title", "News")),
                n.get("url", ""),
                n.get("title", "")
            ))

    # If feedback mentions needing more financial detail and we have stock data
    if all_stock_data and any(k in feedback for k in ["财务", "指标", "季度", "报表", "数据"]):
        for section_name, section_data in all_stock_data.items():
            if section_name not in existing_result.get("financial_data", {}):
                existing_result["financial_data"][section_name] = section_data
                if "citation" in section_data:
                    existing_result["citations"].append(section_data["citation"])

    existing_result["search_queries_used"].extend(new_queries)
    existing_result["refinement_rounds"].append(round_data)

    return existing_result


# ============================================================
#  LEGACY SINGLE-FETCH FUNCTIONS (kept for compatibility)
# ============================================================

def fetch_profile(ticker: str) -> dict:
    """Company profile."""
    if not HAS_YFINANCE:
        return {"error": "yfinance 未安装"}
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
            "citation": _citation("Yahoo Finance", f"https://finance.yahoo.com/quote/{ticker}/", f"{ticker} 公司概况")
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_key_metrics(ticker: str) -> dict:
    if not HAS_YFINANCE:
        return {"error": "yfinance 未安装"}
    try:
        t = yf.Ticker(ticker)
        info = t.info
        data = {
            "P/E (TTM)": info.get("trailingPE", "N/A"),
            "P/E (Forward)": info.get("forwardPE", "N/A"),
            "PEG": info.get("pegRatio", "N/A"),
            "P/B": info.get("priceToBook", "N/A"),
        }
        return {"data": data, "citation": _citation("Yahoo Finance", f"https://finance.yahoo.com/quote/{ticker}/key-statistics/")}
    except Exception as e:
        return {"error": str(e)}


def fetch_financials(ticker: str) -> dict:
    if not HAS_YFINANCE:
        return {"error": "yfinance 未安装"}
    return {"data": {}, "note": "Use fetch_all_stock_data instead"}


def fetch_analyst(ticker: str) -> dict:
    if not HAS_YFINANCE:
        return {"error": "yfinance 未安装"}
    try:
        t = yf.Ticker(ticker)
        info = t.info
        data = {
            "综合评级": info.get("recommendationKey", "N/A"),
            "分析师数量": info.get("numberOfAnalystOpinions", "N/A"),
            "目标均价": info.get("targetMeanPrice", "N/A"),
        }
        return {"data": data, "citation": _citation("Yahoo Finance", f"https://finance.yahoo.com/quote/{ticker}/analysis/")}
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
