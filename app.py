# ─────────────────────────────────────────────────────────────
# WEB RESEARCH AGENT — STREAMLIT UI
#
# This file creates a visual web interface for the research agent.
# Streamlit turns Python code into a web app automatically.
# No HTML, CSS or JavaScript needed.
# ─────────────────────────────────────────────────────────────

import streamlit as st
import anthropic
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

# ─────────────────────────────────────────────────────────────
# PAGE CONFIGURATION
# Must be the first Streamlit command in the file
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Research Agent",
    page_icon="🔍",
    layout="wide"
)

# ─────────────────────────────────────────────────────────────
# CUSTOM STYLING
# ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .search-log {
        background: #f8f9fa;
        border-left: 3px solid #1a1a2e;
        padding: 10px 15px;
        margin: 5px 0;
        border-radius: 0 8px 8px 0;
        font-size: 0.85rem;
        color: #444;
    }
    .report-section {
        background: white;
        padding: 20px;
        border-radius: 12px;
        margin: 10px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .source-link {
        color: #1a1a2e;
        text-decoration: none;
        font-size: 0.9rem;
    }
    .finding-item {
        background: #f0f4ff;
        padding: 10px 15px;
        border-radius: 8px;
        margin: 5px 0;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# INITIALISE CLIENTS
# We use st.cache_resource to create the clients once
# and reuse them — avoids reconnecting on every interaction
# ─────────────────────────────────────────────────────────────

@st.cache_resource
def get_clients():
    client = anthropic.Anthropic()
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    return client, tavily

client, tavily = get_clients()

# ─────────────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────────────

tools = [
    {
        "name": "web_search",
        "description": "Search the web for information on a topic. Use multiple times with different queries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "academic_search",
        "description": "Search specifically for academic papers and research studies",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Academic search query"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "finish_research",
        "description": "Call when you have enough information to write a comprehensive report",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Comprehensive summary of findings"
                },
                "key_findings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of key findings"
                },
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of source URLs"
                }
            },
            "required": ["summary", "key_findings", "sources"]
        }
    }
]

# ─────────────────────────────────────────────────────────────
# TOOL FUNCTIONS
# ─────────────────────────────────────────────────────────────

def web_search(query, log_container):
    log_container.markdown(f'<div class="search-log">🔍 Searching: <em>{query}</em></div>',
                          unsafe_allow_html=True)
    results = tavily.search(query=query, max_results=5, search_depth="advanced")
    formatted = []
    for r in results.get("results", []):
        formatted.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", "")
        })
    return {"results": formatted}


def academic_search(query, log_container):
    log_container.markdown(f'<div class="search-log">📚 Academic search: <em>{query}</em></div>',
                          unsafe_allow_html=True)
    academic_query = f"{query} research study academic paper"
    results = tavily.search(
        query=academic_query,
        max_results=5,
        search_depth="advanced",
        include_domains=[
            "scholar.google.com",
            "pubmed.ncbi.nlm.nih.gov",
            "researchgate.net",
            "arxiv.org",
            "sciencedirect.com",
            "springer.com",
            "nature.com",
            "ieee.org"
        ]
    )
    formatted = []
    for r in results.get("results", []):
        formatted.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
            "type": "academic"
        })
    return {"results": formatted}


# ─────────────────────────────────────────────────────────────
# RESEARCH AGENT
# ─────────────────────────────────────────────────────────────

def run_research_agent(topic, research_mode, max_searches, log_container):
    
    # Adjust system prompt based on mode
    if research_mode == "Academic":
        mode_instruction = "Focus on academic papers, studies and peer-reviewed research. Use academic_search tool primarily."
    else:
        mode_instruction = "Search for general information, news and analysis. Use web_search tool primarily."

    messages = [{
        "role": "user",
        "content": f"""Research this topic thoroughly: {topic}

Mode: {research_mode}
{mode_instruction}

Use search tools multiple times with different queries.
When you have enough information call finish_research.
Maximum searches: {max_searches}"""
    }]

    system = """You are an autonomous research agent. Research topics thoroughly by searching multiple times and synthesising findings.

For each topic:
1. Plan 3-5 different search angles
2. Search for each angle
3. Identify gaps and search to fill them
4. Call finish_research when satisfied

Be systematic. Each query should be specific and different."""

    search_count = 0
    final_report = None

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "web_search":
                        search_count += 1
                        result = web_search(block.input["query"], log_container)
                        if search_count >= max_searches:
                            result["warning"] = "Maximum searches reached. Call finish_research now."

                    elif block.name == "academic_search":
                        search_count += 1
                        result = academic_search(block.input["query"], log_container)
                        if search_count >= max_searches:
                            result["warning"] = "Maximum searches reached. Call finish_research now."

                    elif block.name == "finish_research":
                        log_container.markdown(
                            '<div class="search-log">✅ Research complete — writing report...</div>',
                            unsafe_allow_html=True
                        )
                        result = block.input
                        final_report = block.input

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })

            messages.append({"role": "user", "content": tool_results})

            if final_report:
                break

    return final_report


# ─────────────────────────────────────────────────────────────
# MAIN UI
# ─────────────────────────────────────────────────────────────

# Header
st.markdown('<p class="main-header">🔍 AI Research Agent</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Autonomous web research powered by Claude AI</p>',
           unsafe_allow_html=True)

st.divider()

# Input section
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    topic = st.text_input(
        "Research topic",
        placeholder="e.g. impact of AI on education, climate change solutions, Anthropic company...",
        label_visibility="collapsed"
    )

with col2:
    research_mode = st.selectbox(
        "Mode",
        ["General", "Academic"],
        label_visibility="collapsed"
    )

with col3:
    max_searches = st.selectbox(
        "Max searches",
        [3, 5, 8, 10],
        index=1,
        label_visibility="collapsed"
    )

search_button = st.button("🔍 Research", type="primary", use_container_width=True)

# Run research when button clicked
if search_button and topic:
    st.divider()

    # Activity log
    st.markdown("#### 🤖 Agent Activity")
    log_container = st.container()

    with st.spinner("Researching..."):
        research_data = run_research_agent(
            topic, research_mode, max_searches, log_container
        )

    if research_data:
        st.divider()
        st.markdown("#### 📋 Research Report")

        # Executive Summary
        with st.container():
            st.markdown("**Executive Summary**")
            st.write(research_data.get("summary", ""))

        st.divider()

        # Key Findings
        st.markdown("**Key Findings**")
        for finding in research_data.get("key_findings", []):
            st.markdown(f'<div class="finding-item">• {finding}</div>',
                       unsafe_allow_html=True)

        st.divider()

        # Sources
        st.markdown("**Sources**")
        sources = research_data.get("sources", [])
        for i, source in enumerate(sources, 1):
            st.markdown(f"[{i}] {source}")

        st.divider()

        # Download button
        report_text = f"""RESEARCH REPORT: {topic}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

EXECUTIVE SUMMARY
{research_data.get('summary', '')}

KEY FINDINGS
{chr(10).join(f'• {f}' for f in research_data.get('key_findings', []))}

SOURCES
{chr(10).join(f'[{i+1}] {s}' for i, s in enumerate(research_data.get('sources', [])))}
"""
        st.download_button(
            label="📥 Download Report",
            data=report_text,
            file_name=f"research_{topic[:30].replace(' ', '_')}.txt",
            mime="text/plain"
        )

elif search_button and not topic:
    st.warning("Please enter a research topic.")
    