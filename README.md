# Autonomous Web Research Agent

An AI agent that autonomously searches the web, reads multiple sources 
and produces structured research reports. Features a clean Streamlit UI.

## What It Does

- Receives a research topic from the user
- Autonomously decides what to search for
- Searches the web multiple times with different queries
- Supports Academic mode for finding research papers
- Synthesises findings into a structured report
- Displays results in a clean web interface
- Report downloadable as a text file

## Architecture
Topic Input → Agent Plans Searches → Web Search (Tavily) → Synthesise → Report

## Tech Stack
- Claude API (Anthropic) → AI brain and autonomous decision making
- Tavily API → web search built for AI agents
- Streamlit → web interface
- Python
- python-dotenv

## How to Run
1. Clone the repository
2. Install: `pip install anthropic tavily-python streamlit python-dotenv`
3. Create `.env` with:
   - `ANTHROPIC_API_KEY=your_key`
   - `TAVILY_API_KEY=your_key`
4. Run: `streamlit run app.py`
5. 
