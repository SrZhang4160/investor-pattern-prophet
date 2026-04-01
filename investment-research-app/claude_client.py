"""
Claude API integration for investment research analysis.
Handles dimension suggestions, data analysis, pattern extensions, and rule inference.
"""

import os
import json
from typing import Optional

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


def _find_api_key() -> str:
    """Try to find API key from env var, .env file, or config files in current directory."""
    # 1. Environment variable (standard)
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key

    # 2. .env file
    for env_file in [".env", "../.env"]:
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("ANTHROPIC_API_KEY"):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                return val
            except Exception:
                pass

    # 3. config.md or any .md / .txt file containing the key (user mentioned this)
    for pattern in ["config.md", "config.txt", "api_key.md", "api_key.txt"]:
        if os.path.exists(pattern):
            try:
                with open(pattern, 'r') as f:
                    content = f.read().strip()
                    # Look for something that looks like an API key
                    for line in content.split("\n"):
                        line = line.strip()
                        if "sk-ant-" in line:
                            # Extract the key
                            for word in line.split():
                                if word.startswith("sk-ant-"):
                                    return word.strip("`").strip('"').strip("'")
                        if line.startswith("ANTHROPIC_API_KEY"):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'").strip("`")
                            if val:
                                return val
            except Exception:
                pass

    return ""


def get_client():
    if not HAS_ANTHROPIC:
        return None
    api_key = _find_api_key()
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def is_available() -> bool:
    return HAS_ANTHROPIC and bool(_find_api_key())


def _call(system: str, user_msg: str, max_tokens: int = 2000) -> str:
    client = get_client()
    if not client:
        return "[Claude API 不可用 — 请设置 ANTHROPIC_API_KEY 环境变量]"
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_msg}]
        )
        return response.content[0].text
    except Exception as e:
        return f"[API 错误: {e}]"


# ---------- Dimension Suggestions ----------

def suggest_dimensions(topic: str, research_type: str, existing_dims: list,
                       pattern_context: str = "") -> str:
    """Given a topic and type, suggest research dimensions.
    Returns structured text: one dimension per line, format '维度名称 — 说明'.
    """
    system = """你是一位资深投资研究助手。根据用户的投资研究主题和类型，推荐应该调研的数据维度。

要求：
- 每个维度一行，严格格式：维度名称 — 简短说明为什么重要
- 维度名称要简短精确（2-8个字），方便直接作为研究维度使用
- 如果有已有的维度列表，在此基础上补充，不要重复已有维度
- 推荐 3-5 个额外维度
- 不要推荐买卖建议相关的维度
- 不要加序号、bullet、markdown格式，纯文本每行一个
- 用中文回答"""

    msg = f"""研究主题：{topic}
研究类型：{research_type}
已有维度：{', '.join(existing_dims) if existing_dims else '无'}
{f'用户的历史研究偏好：{pattern_context}' if pattern_context else ''}

请推荐额外应该关注的研究维度："""

    return _call(system, msg)


# ---------- Deep Dimension Analysis ----------

def analyze_dimension_deep(dimension: str, research_result: dict, topic: str) -> str:
    """
    Deep analysis of a dimension based on ALL collected data:
    financial data + web search results + news.
    This is the core analysis function — it synthesizes everything.
    """
    system = """你是一位顶级投资研究分析师。你的任务是基于搜集到的【真实数据和搜索结果】，为指定维度写一份完整的研究摘要。

=== 铁律 ===
1. 【只使用提供给你的数据和搜索结果】。绝对不能编造任何数据、数字或事实。
2. 每一个数据点、每一句事实性陈述后面，都必须标注来源，格式：
   [Source: 来源名称, URL]
   如果是财务数据，标注：[Source: Yahoo Finance, URL]
   如果是搜索结果，标注搜索结果中给出的标题和URL
3. 如果提供的搜索结果中找不到某方面的数据，直接写："⚠️ 此信息在当前搜索结果中未找到，建议手动补充"。不要猜测。

=== 输出格式 ===

**核心发现**
- 列出 3-8 个从数据中提取的关键发现，每条带引用
- 数字要精确，直接引用原始数据

**深度解读**
- 这些数据放在一起意味着什么
- 有哪些值得关注的趋势或异常
- 与行业/历史相比如何（如果搜索结果中有相关信息）

**数据质量评估**
- 数据完整度如何
- 还缺什么关键数据
- 有没有来源之间的矛盾

**来源汇总**
- 列出本分析引用的所有来源（名称 + URL）

=== 其他 ===
- 不做买卖推荐
- 用中文回答，数字和专有名词保留英文
- 尽可能全面，宁多勿少"""

    # Build comprehensive context from all sources
    context_parts = []

    # Financial data
    fin_data = research_result.get("financial_data", {})
    if fin_data:
        context_parts.append("=== 财务数据 (Yahoo Finance) ===")
        for section_name, section in fin_data.items():
            if "data" in section:
                context_parts.append(f"\n【{section_name}】")
                context_parts.append(json.dumps(section["data"], ensure_ascii=False, default=str))
                if "citation" in section:
                    context_parts.append(f"来源: {section['citation']['source']} - {section['citation']['url']}")

    # Web search results
    web_results = research_result.get("web_results", [])
    if web_results:
        context_parts.append("\n=== 网页搜索结果 ===")
        for i, r in enumerate(web_results, 1):
            context_parts.append(f"\n[{i}] {r.get('title', 'N/A')}")
            context_parts.append(f"    URL: {r.get('url', 'N/A')}")
            context_parts.append(f"    摘要: {r.get('snippet', 'N/A')}")

    # News
    news = research_result.get("news_results", [])
    if news:
        context_parts.append("\n=== 近期新闻 ===")
        for i, n in enumerate(news, 1):
            context_parts.append(f"\n[新闻{i}] {n.get('title', 'N/A')}")
            context_parts.append(f"    来源: {n.get('source', 'N/A')} | 日期: {n.get('date', 'N/A')}")
            context_parts.append(f"    URL: {n.get('url', 'N/A')}")
            context_parts.append(f"    内容: {n.get('snippet', 'N/A')}")

    # Search queries used
    queries = research_result.get("search_queries_used", [])
    if queries:
        context_parts.append(f"\n=== 使用的搜索关键词 ===\n{', '.join(queries)}")

    context = "\n".join(context_parts)

    msg = f"""研究主题：{topic}
分析维度：{dimension}

以下是为此维度搜集到的所有真实数据和搜索结果：

{context}

请基于以上【真实搜索结果和数据】做深度分析。只引用上面提供的来源，不要编造数据。"""

    return _call(system, msg, max_tokens=2500)


# ---------- Pattern Extensions ----------

def suggest_extensions(topic: str, research_type: str,
                       collected_dimensions: list,
                       pattern_rules: list,
                       session_history: list) -> str:
    """Based on collected data and patterns, suggest additional research angles."""
    system = """你是一位投资研究助手。根据已完成的研究维度和用户的历史研究模式，建议额外值得探索的方向。

要求：
- 每个建议说明"为什么"值得探索（基于已有数据的逻辑延伸）
- 如果用户有历史 pattern，引用相关 pattern 说明
- 最多 3-5 个建议
- 用中文回答"""

    history_str = ""
    if session_history:
        recent = session_history[-3:]
        history_str = "\n".join([f"- {s.get('topic', '')} ({s.get('type', '')}): 使用了 {', '.join(s.get('dimensions_used', []))}"
                                  for s in recent])

    rules_str = "\n".join([f"- {r['name']}: {r['condition']} → {r['action']}" for r in pattern_rules]) if pattern_rules else "暂无"

    msg = f"""研究主题：{topic}
研究类型：{research_type}
已完成的维度：{', '.join(collected_dimensions)}
用户的判断规则：
{rules_str}
近期研究历史：
{history_str if history_str else '暂无'}

基于以上信息，建议还应该探索哪些方向？"""

    return _call(system, msg, max_tokens=1500)


# ---------- Rule Application ----------

def apply_rules_to_data(rules: list, data_summary: str, topic: str) -> str:
    """Apply judgment rules to collected data and report results."""
    if not rules:
        return "暂无已设置的判断规则。"

    system = """你是一位投资研究助手。将用户预设的判断规则逐条应用到已收集的数据上。

要求：
- 逐条规则判断，格式：
  ✅/❌/⚠️ 规则名称
  条件：xxx
  结果：具体数值和判断（满足/不满足/数据不足）
  数据来源：xxx
- 如果数据不足以判断某条规则，标记为 ⚠️ 并说明缺少什么
- 不做超出规则的主观判断
- 用中文回答"""

    rules_str = "\n".join([f"规则 {r['id']}: {r['name']}\n  条件: {r['condition']}\n  动作: {r['action']}"
                           for r in rules])

    msg = f"""研究主题：{topic}

判断规则：
{rules_str}

已收集的数据摘要：
{data_summary}

请逐条应用规则："""

    return _call(system, msg, max_tokens=2000)


# ---------- Pattern Inference ----------

def infer_patterns(topic: str, research_type: str,
                   dimensions_used: list, user_actions: list) -> str:
    """Based on the user's actions in a session, infer potential new patterns."""
    system = """你是一位投资研究助手。根据用户在本次研究中的行为，推断可能的新 pattern（研究习惯、偏好、规则）。

要求：
- 区分"用户明确表述的"（高置信度）和"从行为推断的"（中/低置信度）
- 格式清晰，每个 pattern 一条
- 包括：框架偏好、数据源偏好、判断规则、排除项
- 用中文回答"""

    actions_str = "\n".join([f"- {a}" for a in user_actions])

    msg = f"""研究主题：{topic}
研究类型：{research_type}
使用的维度：{', '.join(dimensions_used)}

用户在本次研究中的操作和反馈：
{actions_str}

推断出哪些新的研究 pattern？"""

    return _call(system, msg, max_tokens=1500)


# ---------- Research Summary ----------

def generate_summary(topic: str, research_type: str,
                     dimension_results: dict, rule_results: str,
                     open_questions: list) -> str:
    """Generate a final research summary."""
    system = """你是一位投资研究助手。生成一份结构化的研究总结。

要求：
- 开头 2-3 句话的核心发现概述（纯事实，不带观点）
- 按维度组织关键发现
- 列出所有规则判断结果
- 列出未解决的问题和数据缺口
- 保留所有数据来源引用
- 不做投资建议
- 用中文回答"""

    dims_str = ""
    for dim_name, dim_data in dimension_results.items():
        dims_str += f"\n### {dim_name}\n{json.dumps(dim_data, ensure_ascii=False, default=str)}\n"

    msg = f"""研究主题：{topic}
研究类型：{research_type}

各维度数据：
{dims_str}

规则判断结果：
{rule_results}

未解决问题：
{chr(10).join(['- ' + q for q in open_questions]) if open_questions else '无'}

请生成结构化研究总结："""

    return _call(system, msg, max_tokens=3000)
