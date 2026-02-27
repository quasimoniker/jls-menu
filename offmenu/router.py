import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

ROUTER_PROMPT = """You are a routing assistant for a chatbot about the Off Menu podcast.
The podcast has two types of data available:
1. A structured table of each guest's menu choices (starter, main, dessert, drink, still or sparkling, poppadoms or bread, and occasionally christmas dinner)
2. Full transcripts of each episode

Your job is to classify whether a question can be answered from the structured menu choices table, or whether it requires the transcripts.

Return exactly one of these three labels:
- "csv" — if the question asks about what a guest chose, patterns across guests, counts, most common choices, or any lookup or aggregation of menu choices
- "rag" — if the question asks about what was said, discussed, or happened in an episode — jokes, stories, opinions, context, conversation
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

Return only the label, nothing else."""

def get_route(question: str) -> str:
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[
            {"role": "user", "content": f"{ROUTER_PROMPT}\n\nQuestion: {question}"}
        ]
    )
    label = response.content[0].text.strip().lower().strip('"')
    if label not in ("csv", "rag", "unclear"):
        return "unclear"
    return label