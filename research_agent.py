# ─────────────────────────────────────────────────────────────
# AUTONOMOUS WEB RESEARCH AGENT
#
# This agent receives a topic or company name and autonomously:
# 1. Decides what to search for
# 2. Searches the web using Tavily
# 3. Reads and analyses the results
# 4. Decides if it needs more information
# 5. Produces a structured research report
#
# Key concept: the agent decides its own search queries
# and whether to keep searching — that autonomy is what
# makes it an agent rather than a simple search wrapper.
# ─────────────────────────────────────────────────────────────

import anthropic
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

# Initialise both clients
client = anthropic.Anthropic()
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# ─────────────────────────────────────────────────────────────
# TOOLS
#
# We give the agent two tools:
# 1. web_search — searches the internet and returns results
# 2. finish_research — called when the agent has enough info
#    and is ready to write the final report
#
# The agent decides on its own when to search, what to search
# for, and when it has gathered enough information to stop.
# ─────────────────────────────────────────────────────────────

tools = [
    {
        "name": "web_search",
        "description": "Search the web for information on a topic. Use this multiple times with different queries to gather comprehensive information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to use"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "finish_research",
        "description": "Call this when you have gathered enough information to write a comprehensive report. Pass all the information you have collected.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "A comprehensive summary of all research findings"
                },
                "key_findings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of the most important findings"
                },
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs used as sources"
                }
            },
            "required": ["summary", "key_findings", "sources"]
        }
    }
]


# ─────────────────────────────────────────────────────────────
# TOOL FUNCTIONS
#
# web_search calls Tavily which returns clean search results
# specifically formatted for AI agents — no HTML noise
#
# finish_research just returns the data so the agent loop
# knows when to stop and generate the final report
# ─────────────────────────────────────────────────────────────

def web_search(query):
    print(f"[Searching: '{query}']")
    
    results = tavily.search(
        query=query,
        max_results=5,          # Get top 5 results per search
        search_depth="advanced" # Deep search for better results
    )
    
    # Format results cleanly for Claude to read
    formatted = []
    for r in results.get("results", []):
        formatted.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", "")
        })
    
    print(f"[Found {len(formatted)} results]")
    return {"results": formatted}


def finish_research(summary, key_findings, sources):
    # This just passes the data back — the loop handles the rest
    return {
        "summary": summary,
        "key_findings": key_findings,
        "sources": sources
    }


# ─────────────────────────────────────────────────────────────
# TOOL FUNCTIONS
#
# academic_search calls an academic search function
# (e.g., Google Scholar, Semantic Scholar)
# Returns a dict with results, similar to web_search
# ─────────────────────────────────────────────────────────────

def academic_search(query, **kwargs):
    """
    Placeholder for academic search function.
    Implement logic to search academic sources (e.g., via APIs like Google Scholar or Semantic Scholar).
    Returns a dict with results, similar to web_search.
    """
    # Example implementation (replace with real logic)
    return {"results": f"Academic search results for: {query}", **kwargs}


# ─────────────────────────────────────────────────────────────
# RESEARCH AGENT LOOP
#
# This is an autonomous agent — it decides:
# - What to search for (query formulation)
# - How many searches to do (stops when satisfied)
# - When it has enough information (calls finish_research)
#
# The agent can do up to max_searches searches before
# being forced to write the report. This prevents infinite loops.
# ─────────────────────────────────────────────────────────────

def run_research_agent(topic, max_searches=5):
    print(f"\n{'='*50}")
    print(f"Research Agent starting on: {topic}")
    print(f"{'='*50}\n")
    
    messages = [{
        "role": "user",
        "content": f"""Research this topic thoroughly: {topic}

Instructions:
- Use the web_search tool multiple times with different queries
- Each search should explore a different aspect of the topic
- Gather comprehensive information before writing your report
- When you have enough information call finish_research
- Maximum searches allowed: {max_searches}

Start researching now."""
    }]
    
    system = """You are an autonomous research agent. Your job is to research topics thoroughly by searching the web multiple times and synthesising findings into a clear report.

For each topic:
1. Plan 3-5 different search angles before starting
2. Search for each angle using the web_search tool
3. Analyse what you find and identify gaps
4. Do additional searches to fill those gaps
5. When satisfied call finish_research with your complete findings

Be systematic and thorough. Each search query should be specific and different from previous ones."""

    search_count = 0
    final_report = None
    
    # Agent loop — keeps running until finish_research is called
    # or max_searches is reached
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            tools=tools,
            messages=messages
        )
        
        # Agent finished — either called finish_research or ran out of searches
        if response.stop_reason == "end_turn":
            print("[Agent completed research]")
            break
        
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            
            for block in response.content:
                if block.type == "tool_use":
                    
                    if block.name == "web_search":
                        search_count += 1
                        print(f"[Search {search_count}/{max_searches}]")
                        result = web_search(**block.input)
                        
                        # If max searches reached tell the agent to wrap up
                        if search_count >= max_searches:
                            result["warning"] = "Maximum searches reached. Please call finish_research now."
                    
                    elif block.name == "academic_search":
                        search_count += 1
                        result = academic_search(**block.input)
                        
                    elif block.name == "finish_research":
                        print("[Agent finishing research and writing report...]")
                        result = finish_research(**block.input)
                        final_report = block.input
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })
            
            messages.append({"role": "user", "content": tool_results})
            
            # Stop loop if report is done
            if final_report:
                break
    
    return final_report


# ─────────────────────────────────────────────────────────────
# REPORT WRITER
#
# Takes the raw research data and asks Claude to format it
# into a clean professional report.
# ─────────────────────────────────────────────────────────────

def write_report(topic, research_data):
    print("[Writing final report...]")
    
    response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=2048,
    messages=[{
        "role": "user",
        "content": f"""Write a clear professional research report on: {topic}

Use this research data:
{json.dumps(research_data, indent=2)}

Format the report EXACTLY like this:

EXECUTIVE SUMMARY
[2-3 sentence overview]

KEY FINDINGS
- [finding 1]
- [finding 2]
- [finding 3]
- [finding 4]
- [finding 5]

DETAILED ANALYSIS
[2-3 paragraphs of analysis]

SOURCES
[1] [title] — [url]
[2] [title] — [url]
[3] [title] — [url]

Keep it concise and professional."""
    }]
)

    return response.content[0].text


# ─────────────────────────────────────────────────────────────
# SAVE REPORT
#
# Saves the report to a file so you can reference it later
# Filename includes the topic and timestamp
# ─────────────────────────────────────────────────────────────

def save_report(topic, report):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean topic name for use as filename
    clean_topic = "".join(c if c.isalnum() else "_" for c in topic)
    filename = f"report_{clean_topic}_{timestamp}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"RESEARCH REPORT: {topic}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(report)
    
    print(f"[Report saved to {filename}]")
    return filename


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("Autonomous Web Research Agent")
    print("=" * 50)
    print("Type 'quit' to exit\n")
    
    while True:
        topic = input("Research topic: ")
        if topic.lower() == "quit":
            break
        
        # Step 1: Run the research agent
        research_data = run_research_agent(topic)
        
        if research_data:
            # Step 2: Write a clean report from the research
            report = write_report(topic, research_data)
            
            # Step 3: Print the report
            print("\n" + "="*50)
            print("FINAL REPORT")
            print("="*50)
            print(report)
            
            # Step 4: Save to file
            save_report(topic, report)
        else:
            print("[Research failed — try again]")
        
        print("\n" + "="*50 + "\n")
    
main()
