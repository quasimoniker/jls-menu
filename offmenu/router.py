import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

def get_secret(key: str) -> str:
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        return os.getenv(key)
    
anthropic_client = anthropic.Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))

ROUTER_PROMPT = """You are a routing assistant for a chatbot about the Off Menu podcast.
The podcast has two types of data available:
1. A structured table of each guest's menu choices (starter, main, side dish, dessert, drink, still or sparkling, poppadoms or bread, and occasionally christmas dinner)
2. Full transcripts of each episode

Your job is to classify incoming questions into one of four categories.

Return exactly one of these four labels:
- "csv" — if the question asks about what a guest chose, patterns across guests, counts, most common choices, or any lookup or aggregation of menu choices
- "rag" — if the question asks about what was said, discussed, or happened in an episode — jokes, stories, opinions, context, conversation
- "meta" — if the question is about the chatbot itself, its capabilities, how many episodes it has access to, or what it knows
- "unclear" — if you cannot confidently determine which type it is

Examples:
"what's the most common starter?" → csv
"which guests chose pizza?" → csv
"what did Ed Sheeran choose as his main?" → csv
"has anyone ever picked a Greggs sausage roll?" → csv
"what did James Acaster say about curry?" → rag
"why did Adele choose her dessert?" → rag
"what's the vibe of the podcast?" → rag
"did any guest get emotional?" → rag
"who are you?" → meta
"how many episodes do you have access to?" → meta
"what can you help me with?" → meta
"what do you know?" → meta

Return only the label, nothing else."""

def get_route(question: str) -> str:
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": f"{ROUTER_PROMPT}\n\nQuestion: {question}"
        }]
    )
    label = response.content[0].text.strip().lower().strip('"')
    if label not in ("csv", "rag", "meta", "unclear"):
        return "unclear"
    return label