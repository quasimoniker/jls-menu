import os
import voyageai
from pinecone import Pinecone
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

PINECONE_INDEX = "offmenu"
EMBEDDING_MODEL = "voyage-3-lite"
TOP_K = 10  # number of chunks to retrieve

def get_secret(key: str) -> str:
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        return os.getenv(key)
    
voyage = voyageai.Client(api_key=get_secret("VOYAGE_API_KEY"))
pc = Pinecone(api_key=get_secret("PINECONE_API_KEY"))
index = pc.Index(PINECONE_INDEX)
anthropic = Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))
    
def find_episode_filter(question):
    import csv
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "menu_choices.csv")
    
    lookup = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            guest = row["guest"].strip().lower()
            lookup[guest] = row["episode"]
    
    question_lower = question.lower()
    for guest, episode in lookup.items():
        if guest in question_lower:
            return episode
    
    return None

def retrieve(question):
    episode_filter = find_episode_filter(question)

    result = voyage.embed([question], model=EMBEDDING_MODEL, input_type="query")
    query_embedding = result.embeddings[0]

    if episode_filter:
        print(f"(Filtering to episode {episode_filter})")
        results = index.query(
            vector=query_embedding,
            top_k=20,
            include_metadata=True,
            filter={"episode": {"$eq": episode_filter}}
        )
    else:
        results = index.query(
            vector=query_embedding,
            top_k=TOP_K,
            include_metadata=True
        )

    chunks = []
    for match in results.matches:
        chunks.append({
            "episode": match.metadata["episode"],
            "guest": match.metadata["guest"],
            "text": match.metadata["text"],
            "score": match.score
        })
    return chunks

def build_prompt(question, chunks):
    context = ""
    for chunk in chunks:
        context += f"[Ep {chunk['episode']} – {chunk['guest']}]\n{chunk['text']}\n\n"

    return f"""You are a helpful assistant with expertise on the Off Menu podcast, hosted by Ed Gamble and James Acaster. 
Answer the question using only the transcript excerpts provided below. 
If the answer isn't in the excerpts, say so honestly rather than guessing.
Always mention which episode and guest the information comes from.

TRANSCRIPT EXCERPTS:
{context}

QUESTION: {question}"""

def ask(question):
    chunks = retrieve(question)
    prompt = build_prompt(question, chunks)

    response = anthropic.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

def main():
    print("Off Menu Chatbot (type 'quit' to exit)\n")
    while True:
        question = input("You: ").strip()
        if question.lower() == "quit":
            break
        if not question:
            continue
        print("\nClaude:", ask(question))
        print()

if __name__ == "__main__":
    main()