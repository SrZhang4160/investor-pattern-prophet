"""
Investment Research Agent — Streamlit Web Application

Two roles:
  - Trainer (pattern owner): runs research sessions, trains patterns
  - User (everyone else): follows the trained patterns for guided research

Run: streamlit run app.py
"""

import streamlit as st
import json
import os
from datetime import datetime

from pattern_memory import PatternMemory, DEFAULT_DIMENSIONS
from data_collector import (fetch_profile, fetch_key_metrics, fetch_financials, fetch_analyst,
                            fetch_all_stock_data, get_relevant_data_for_dimension,
                            research_dimension, check_dependencies)
import claude_client

# ---------- Config ----------

PATTERN_FILE = os.environ.get("PATTERN_MEMORY_PATH", "pattern_memory.json")
TRAINER_PASSWORD = os.environ.get("TRAINER_PASSWORD", "alanPattern")  # Change in production

st.set_page_config(
    page_title="投研助手 — Investment Research Agent",
    page_icon="📊",
    layout="wide"
)


# ---------- Session State Init ----------

def init_state():
    defaults = {
        "role": None,
        "pm": PatternMemory(PATTERN_FILE),
        "step": 0,
        "topic": "",
        "research_type": "company_deep_dive",
        "selected_dims": [],
        "dim_data": {},
        "current_dim_idx": 0,
        "rule_results": "",
        "extensions": "",
        "summary": "",
        "user_actions": [],
        "open_questions": [],
        "ticker": "",
        "all_stock_data": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()
pm: PatternMemory = st.session_state.pm


# ---------- Sidebar ----------

def sidebar():
    st.sidebar.title("📊 投研助手")

    if pm.exists():
        s = pm.summary()
        st.sidebar.success(f"Pattern 已加载 — {s['owner']}")
        st.sidebar.caption(f"维度: {s['total_dimensions']} | 规则: {s['active_rules']} | 历史: {s['total_sessions']} 次研究")
    else:
        st.sidebar.warning("Pattern 未初始化")

    st.sidebar.divider()

    # Role selection
    if st.session_state.role is None:
        st.sidebar.subheader("选择身份")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.sidebar.button("🎓 训练者", use_container_width=True):
                st.session_state.role = "pending_trainer"
                st.rerun()
        with col2:
            if st.sidebar.button("👤 使用者", use_container_width=True):
                st.session_state.role = "user"
                st.rerun()
    else:
        role_label = "🎓 训练者" if st.session_state.role == "trainer" else "👤 使用者"
        st.sidebar.info(f"当前身份: {role_label}")
        if st.sidebar.button("切换身份"):
            st.session_state.role = None
            st.session_state.step = 0
            st.rerun()

    st.sidebar.divider()

    # Pattern management
    st.sidebar.subheader("Pattern 管理")

    # Export
    if pm.exists():
        export_data = pm.export_json()
        st.sidebar.download_button(
            "📤 导出 Pattern",
            data=export_data,
            file_name=f"pattern_memory_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )

    # Import
    uploaded = st.sidebar.file_uploader("📥 导入 Pattern", type=["json"], key="import_pattern")
    if uploaded:
        try:
            imported = json.loads(uploaded.read().decode("utf-8"))
            if "version" in imported and "research_frameworks" in imported:
                merge = st.sidebar.checkbox("合并模式（保留已有，添加新的）", value=True)
                if st.sidebar.button("确认导入"):
                    pm.import_from_dict(imported, merge=merge)
                    st.session_state.pm = PatternMemory(PATTERN_FILE)
                    st.sidebar.success(f"导入成功！来源: {imported.get('owner', {}).get('name', '未知')}")
                    st.rerun()
            else:
                st.sidebar.error("文件格式不正确")
        except json.JSONDecodeError:
            st.sidebar.error("JSON 解析失败")

    # Dependencies check
    st.sidebar.divider()
    deps = check_dependencies()
    claude_ok = claude_client.is_available()
    with st.sidebar.expander("系统状态"):
        st.write(f"yfinance: {'✅' if deps['yfinance'] else '❌ pip install yfinance'}")
        st.write(f"Claude API: {'✅' if claude_ok else '❌ 设置 ANTHROPIC_API_KEY'}")


sidebar()


# ---------- Trainer Auth ----------

if st.session_state.role == "pending_trainer":
    st.title("🔐 训练者验证")
    st.caption("只有 pattern 所有者可以训练和修改 pattern。")
    pwd = st.text_input("输入训练者密码：", type="password")
    if st.button("验证"):
        if pwd == TRAINER_PASSWORD:
            st.session_state.role = "trainer"
            st.rerun()
        else:
            st.error("密码错误")
    st.stop()


# ---------- No Role Selected ----------

if st.session_state.role is None:
    st.title("📊 投研助手 — Investment Research Agent")
    st.markdown("""
    一个学习投资研究 pattern 的 AI 助手。

    **两种使用方式：**

    **🎓 训练者** — 做真实的投资研究，agent 边帮你查数据边学习你的研究习惯
    （框架、数据偏好、判断规则）。训练的 pattern 可以导出分享。

    **👤 使用者** — 输入投资 topic，按照训练者的研究框架获得引导式研究，
    包括推荐维度、数据采集、规则判断。

    👈 从左侧选择身份开始。
    """)
    st.stop()


# ============================================================
#  RESEARCH WORKFLOW (shared by trainer and user)
# ============================================================

RESEARCH_TYPES = {
    "company_deep_dive": "个股深度分析",
    "industry_landscape": "行业/板块全景",
    "macro_theme": "宏观主题分析",
    "comparative_analysis": "多标的对比",
    "event_driven": "事件驱动分析",
}

is_trainer = st.session_state.role == "trainer"
step = st.session_state.step


# ---------- Step 0: Initialize Pattern ----------

if step == 0:
    if not pm.exists() and is_trainer:
        st.title("🚀 初始化 Pattern Memory")
        name = st.text_input("你的名字（Pattern 所有者）：", value="Sharon")
        if st.button("创建 Pattern Memory"):
            pm.initialize(name)
            st.session_state.pm = PatternMemory(PATTERN_FILE)
            st.success(f"Pattern Memory 已创建！所有者：{name}")
            st.session_state.step = 1
            st.rerun()
    elif not pm.exists() and not is_trainer:
        st.title("📊 投研助手")
        st.warning("还没有训练过的 Pattern。请导入一个 Pattern 文件（左侧 📥 导入），或联系训练者获取。")
        st.stop()
    else:
        st.session_state.step = 1
        st.rerun()


# ---------- Step 1: Topic & Scope ----------

elif step == 1:
    st.title("📋 Step 1 — 研究主题与范围")

    if pm.exists() and not is_trainer:
        owner = pm.get_owner()
        st.info(f"当前使用 **{owner}** 的研究 pattern。你的操作不会修改原始 pattern。")

    st.session_state.topic = st.text_input(
        "投资研究主题：",
        value=st.session_state.topic,
        placeholder="例如：NVIDIA AI 基础设施、东南亚电动车供应链、美联储降息对REITs的影响"
    )

    st.session_state.research_type = st.selectbox(
        "研究类型：",
        options=list(RESEARCH_TYPES.keys()),
        format_func=lambda x: RESEARCH_TYPES[x],
        index=list(RESEARCH_TYPES.keys()).index(st.session_state.research_type)
    )

    # Ticker input for company research
    if st.session_state.research_type in ("company_deep_dive", "comparative_analysis"):
        st.session_state.ticker = st.text_input(
            "股票代码（可选，用于自动拉取财务数据）：",
            value=st.session_state.ticker,
            placeholder="例如：NVDA, AAPL, 0700.HK"
        )

    # Dimension selection
    st.subheader("选择研究维度")

    rtype = st.session_state.research_type
    available_dims = pm.get_dimensions(rtype)

    # Show which are from pattern vs defaults
    pattern_dims = pm.get_dimension_details(rtype)
    if pattern_dims:
        st.caption(f"📝 以下维度来自训练者的研究 pattern（{len(pattern_dims)} 个已学习维度）")
    else:
        st.caption("📝 使用默认维度列表（训练后会根据你的偏好调整）")

    selected = []
    cols = st.columns(2)
    for i, dim in enumerate(available_dims):
        with cols[i % 2]:
            if st.checkbox(dim, value=True, key=f"dim_{dim}"):
                selected.append(dim)

    # Custom dimensions
    custom = st.text_input("添加自定义维度（逗号分隔）：", placeholder="例如：ESG评级, 管理层持股")
    if custom:
        for d in custom.split(","):
            d = d.strip()
            if d and d not in selected:
                selected.append(d)

    # Claude suggestions
    if st.session_state.topic and claude_client.is_available():
        with st.expander("🤖 AI 建议额外维度"):
            if st.button("获取 AI 建议"):
                with st.spinner("分析中..."):
                    suggestions = claude_client.suggest_dimensions(
                        st.session_state.topic,
                        RESEARCH_TYPES[rtype],
                        selected,
                        json.dumps(pm.get_active_rules(), ensure_ascii=False) if pm.exists() else ""
                    )
                    st.markdown(suggestions)

    st.divider()

    if st.button("✅ 确认维度，开始采集数据", type="primary", disabled=not st.session_state.topic):
        st.session_state.selected_dims = selected
        st.session_state.dim_data = {}
        st.session_state.current_dim_idx = 0
        st.session_state.user_actions.append(f"选择了研究类型 {RESEARCH_TYPES[rtype]}，维度: {', '.join(selected)}")
        st.session_state.step = 2
        st.rerun()


# ---------- Step 2: Data Collection ----------

elif step == 2:
    st.title("📡 Step 2 — 数据采集与分析")

    dims = st.session_state.selected_dims
    current_idx = st.session_state.current_dim_idx
    topic = st.session_state.topic
    ticker = st.session_state.ticker

    # --- Step 2a: One-time batch fetch all stock data if ticker provided ---
    if ticker and not st.session_state.all_stock_data:
        with st.spinner(f"🔄 正在从 Yahoo Finance 批量获取 **{ticker}** 的所有数据..."):
            all_data = fetch_all_stock_data(ticker)
        if "error" in all_data and len(all_data) == 1:
            st.error(f"获取失败: {all_data['error']}")
        else:
            st.session_state.all_stock_data = all_data

    # Progress
    progress = current_idx / len(dims) if dims else 0
    st.progress(progress, text=f"进度: {current_idx}/{len(dims)} 个维度")

    if current_idx >= len(dims):
        st.success("🎉 所有维度数据采集完成！")
        if st.button("➡️ 进入下一步: Pattern 引申建议", type="primary"):
            st.session_state.step = 3
            st.rerun()
        st.stop()

    dim = dims[current_idx]
    st.subheader(f"📌 当前维度: {dim} ({current_idx + 1}/{len(dims)})")

    # --- Keys ---
    research_key = f"research_result_{current_idx}_{dim}"
    analysis_key = f"analysis_result_{current_idx}_{dim}"

    # --- Phase 1: Auto collect all data ---
    if research_key not in st.session_state:
        st.session_state[research_key] = None

    if st.session_state[research_key] is None:
        with st.spinner(f"🔍 正在为「{dim}」全面采集数据（财务数据 + 网页搜索 + 新闻）..."):
            result = research_dimension(
                topic=topic, dimension=dim, ticker=ticker,
                all_stock_data=st.session_state.all_stock_data
            )
            st.session_state[research_key] = result
            st.session_state.dim_data[dim] = result
        st.rerun()

    research = st.session_state[research_key]

    # --- Phase 2: Auto AI analysis (no button needed) ---
    if analysis_key not in st.session_state:
        st.session_state[analysis_key] = ""

    if claude_client.is_available() and not st.session_state[analysis_key]:
        with st.spinner(f"🤖 AI 正在基于 {len(research.get('citations', []))} 条来源深度分析「{dim}」..."):
            analysis = claude_client.analyze_dimension_deep(dim, research, topic)
            st.session_state[analysis_key] = analysis
            st.session_state.dim_data[dim]["ai_analysis"] = analysis
        st.rerun()

    # --- Display: AI Summary (main content) ---
    if st.session_state[analysis_key]:
        st.markdown(st.session_state[analysis_key])
    else:
        st.warning("Claude API 未配置，无法生成自动分析。以下为原始数据。")
        # Fallback: show raw financial data
        if research.get("financial_data"):
            for section_name, section_data in research["financial_data"].items():
                st.write(f"**{section_name}**")
                if "data" in section_data:
                    st.json(section_data["data"])
                if "citation" in section_data:
                    c = section_data["citation"]
                    st.caption(f"[Source: {c['source']}, {c['url']}, accessed {c['accessed']}]")

    # --- Collapsed: raw sources for verification ---
    total_sources = len(research.get("citations", []))
    with st.expander(f"📎 原始数据来源 ({total_sources} 条) — 点击展开验证"):
        if research.get("financial_data"):
            st.write("**财务数据:**")
            for section_name, section_data in research["financial_data"].items():
                if "citation" in section_data:
                    c = section_data["citation"]
                    st.caption(f"• {section_name} — {c['source']}, {c['url']}")

        if research.get("web_results"):
            st.write("**网页搜索:**")
            for r in research["web_results"]:
                st.caption(f"• {r.get('title', 'N/A')} — {r.get('url', '')}")

        if research.get("news_results"):
            st.write("**新闻:**")
            for n in research["news_results"]:
                meta = n.get("source", "")
                if n.get("date"):
                    meta += f" ({str(n['date'])[:10]})"
                st.caption(f"• {n.get('title', 'N/A')} — {meta} — {n.get('url', '')}")

        if research.get("search_queries_used"):
            st.write("**搜索关键词:**")
            st.caption(", ".join(research["search_queries_used"]))

    # --- Manual supplement ---
    with st.expander("✏️ 手动补充数据"):
        manual_data = st.text_area(
            f"为「{dim}」添加数据点（每行一条，格式：数据内容 | 来源名称 | URL）",
            height=100, key=f"manual_{dim}"
        )

    # --- Data Quality ---
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        completeness = st.selectbox("完整性", ["✅ 完整", "⚠️ 部分", "❌ 不可用"], key=f"comp_{dim}")
    with col2:
        freshness = st.text_input("时效性", placeholder="例如: 2025-Q4", key=f"fresh_{dim}")
    with col3:
        reliability = st.selectbox("可靠性", ["一手来源", "二手来源", "需要验证"], key=f"rel_{dim}")

    # --- Approval ---
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ 数据可用，下一个维度", type="primary"):
            if manual_data:
                manual_entries = []
                for line in manual_data.strip().split("\n"):
                    parts = line.split("|")
                    manual_entries.append({
                        "content": parts[0].strip(),
                        "source": parts[1].strip() if len(parts) > 1 else "手动输入",
                        "url": parts[2].strip() if len(parts) > 2 else ""
                    })
                st.session_state.dim_data[dim]["manual"] = manual_entries

            st.session_state.user_actions.append(
                f"维度「{dim}」审批通过 | 数据源: {total_sources}条 | 质量: {completeness}"
            )
            st.session_state.current_dim_idx += 1
            st.rerun()
    with col2:
        if st.button("⏭️ 跳过此维度"):
            st.session_state.user_actions.append(f"跳过维度「{dim}」")
            st.session_state.current_dim_idx += 1
            st.rerun()
    with col3:
        note = st.text_input("需要补充：", key=f"note_{dim}", placeholder="还需要查什么")
        if note:
            st.session_state.user_actions.append(f"维度「{dim}」需要补充: {note}")


# ---------- Step 3: Pattern Extensions ----------

elif step == 3:
    st.title("🔍 Step 3 — Pattern 引申建议")

    topic = st.session_state.topic
    rtype = st.session_state.research_type
    collected = list(st.session_state.dim_data.keys())

    if claude_client.is_available():
        with st.spinner("基于已有数据和 pattern 生成建议..."):
            extensions = claude_client.suggest_extensions(
                topic, RESEARCH_TYPES[rtype], collected,
                pm.get_active_rules() if pm.exists() else [],
                pm.get_recent_sessions() if pm.exists() else []
            )
        st.markdown(extensions)
        st.session_state.extensions = extensions
    else:
        st.info("Claude API 未配置，跳过 AI 引申建议。")
        st.markdown("""
        **可以考虑的额外方向：**
        - 检查数据之间的交叉验证
        - 与同行业公司对比
        - 考虑宏观环境影响
        """)

    st.divider()

    extra_dims = st.text_input("想额外探索的方向（逗号分隔，留空跳过）：")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("➡️ 跳过引申，进入规则判断", type="primary"):
            st.session_state.step = 4
            st.rerun()
    with col2:
        if extra_dims and st.button("添加并采集这些维度"):
            new_dims = [d.strip() for d in extra_dims.split(",") if d.strip()]
            st.session_state.selected_dims.extend(new_dims)
            st.session_state.user_actions.append(f"添加引申维度: {', '.join(new_dims)}")
            st.session_state.step = 2  # Go back to data collection
            st.rerun()


# ---------- Step 4: Judgment Rules ----------

elif step == 4:
    st.title("⚖️ Step 4 — 规则判断")

    topic = st.session_state.topic
    rules = pm.get_active_rules() if pm.exists() else []

    if rules:
        st.write(f"**应用 {len(rules)} 条已学习的判断规则：**")

        # Build data summary for rule application
        data_summary = json.dumps(st.session_state.dim_data, ensure_ascii=False, default=str)[:5000]

        if claude_client.is_available():
            with st.spinner("应用规则中..."):
                rule_results = claude_client.apply_rules_to_data(rules, data_summary, topic)
            st.markdown(rule_results)
            st.session_state.rule_results = rule_results
        else:
            st.info("Claude API 未配置。以下为已设置的规则，请手动判断：")
            for r in rules:
                st.write(f"- **{r['name']}**: `{r['condition']}` → {r['action']}")
    else:
        st.info("暂无已学习的判断规则。")

    # Trainer can add new rules
    if is_trainer:
        st.divider()
        st.subheader("➕ 添加新规则")
        st.caption("基于这次研究，你有没有常用的判断逻辑？")

        new_rule_name = st.text_input("规则名称", placeholder="例如：FCF 收益率筛选")
        new_rule_cond = st.text_input("条件", placeholder="例如：FCF_yield > 8%")
        new_rule_action = st.selectbox("满足时动作",
                                        ["flag_for_deeper_analysis", "flag_as_risk", "flag_as_positive_signal", "skip"])
        new_rule_notes = st.text_input("备注", placeholder="为什么这个规则重要？")

        if st.button("保存规则") and new_rule_name and new_rule_cond:
            pm.add_rule(new_rule_name, new_rule_cond, new_rule_action,
                        confidence="high", notes=new_rule_notes)
            pm.save_with_backup()
            st.session_state.pm = PatternMemory(PATTERN_FILE)
            st.session_state.user_actions.append(f"新增规则: {new_rule_name} ({new_rule_cond})")
            st.success(f"规则「{new_rule_name}」已保存！")
            st.rerun()

    st.divider()
    if st.button("➡️ 进入研究总结", type="primary"):
        st.session_state.step = 5
        st.rerun()


# ---------- Step 5: Summary ----------

elif step == 5:
    st.title("📝 Step 5 — 研究总结")

    topic = st.session_state.topic
    rtype = st.session_state.research_type

    # Open questions
    st.subheader("未解决的问题")
    open_q = st.text_area("列出需要继续跟进的问题（每行一条）：", height=100)
    if open_q:
        st.session_state.open_questions = [q.strip() for q in open_q.strip().split("\n") if q.strip()]

    # Generate summary
    if claude_client.is_available():
        if st.button("🤖 生成 AI 研究总结"):
            with st.spinner("生成中..."):
                summary = claude_client.generate_summary(
                    topic, RESEARCH_TYPES[rtype],
                    st.session_state.dim_data,
                    st.session_state.rule_results,
                    st.session_state.open_questions
                )
                st.session_state.summary = summary

    if st.session_state.summary:
        st.divider()
        st.markdown(st.session_state.summary)

        # Download summary
        st.download_button(
            "📄 下载研究报告",
            data=st.session_state.summary,
            file_name=f"research_{topic.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown"
        )

    st.divider()
    if st.button("➡️ 完成研究" + (" & 更新 Pattern" if is_trainer else ""), type="primary"):
        st.session_state.step = 6
        st.rerun()


# ---------- Step 6: Pattern Update (Trainer only) ----------

elif step == 6:
    st.title("🧠 Step 6 — " + ("Pattern 学习" if is_trainer else "研究完成"))

    topic = st.session_state.topic
    rtype = st.session_state.research_type
    dims = st.session_state.selected_dims

    if is_trainer and pm.exists():
        st.subheader("📝 本次学到的 Pattern")

        # Infer patterns from user actions
        if claude_client.is_available() and st.session_state.user_actions:
            with st.spinner("分析研究行为..."):
                inferred = claude_client.infer_patterns(
                    topic, RESEARCH_TYPES[rtype], dims, st.session_state.user_actions
                )
            st.markdown(inferred)

        st.divider()

        # Auto-updates
        st.subheader("建议的 Pattern 更新：")

        # Check for new dimensions to add
        current_dims = pm.get_dimensions(rtype)
        new_dims = [d for d in dims if d not in current_dims and d not in DEFAULT_DIMENSIONS.get(rtype, [])]
        if new_dims:
            st.write(f"**新增维度** ({rtype}): {', '.join(new_dims)}")

        # Sequence update
        st.write(f"**研究顺序**: {' → '.join(dims)}")

        # Session feedback
        feedback = st.text_area("本次研究的反馈/备注：", placeholder="例如：这个 topic 更需要关注供应链数据")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 保存 Pattern 更新", type="primary"):
                # Add new dimensions
                for d in new_dims:
                    pm.add_dimension(rtype, d, notes=f"从「{topic}」研究中学习")

                # Update sequence
                pm.update_sequence(rtype, dims)

                # Log session
                pm.add_session(
                    topic, rtype, dims,
                    [r["id"] for r in pm.get_active_rules()],
                    feedback
                )

                pm.save_with_backup()
                st.session_state.pm = PatternMemory(PATTERN_FILE)
                st.success("Pattern 已更新并保存！")
                st.balloons()

                # Reset for next research
                st.session_state.step = 0
                st.session_state.topic = ""
                st.session_state.dim_data = {}
                st.session_state.user_actions = []
                st.session_state.selected_dims = []
                st.session_state.ticker = ""
                st.session_state.all_stock_data = {}
                st.rerun()

        with col2:
            if st.button("跳过，不保存"):
                st.session_state.step = 0
                st.session_state.topic = ""
                st.session_state.dim_data = {}
                st.session_state.user_actions = []
                st.session_state.selected_dims = []
                st.session_state.ticker = ""
                st.session_state.all_stock_data = {}
                st.rerun()

    else:
        # Non-trainer: just wrap up
        st.success("研究完成！")
        if st.session_state.summary:
            st.download_button(
                "📄 下载研究报告",
                data=st.session_state.summary,
                file_name=f"research_{topic.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown"
            )

        if st.button("🔄 开始新的研究"):
            st.session_state.step = 0
            st.session_state.topic = ""
            st.session_state.dim_data = {}
            st.session_state.user_actions = []
            st.session_state.selected_dims = []
            st.session_state.ticker = ""
            st.session_state.all_stock_data = {}
            st.rerun()
