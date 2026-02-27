import os
import json
import voyageai
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

CHUNKS_FILE = "data/chunks.json"
PINECONE_INDEX = "offmenu"
EMBEDDING_MODEL = "voyage-3-lite"
BATCH_SIZE = 128
TARGET_EPISODES = ("167", "168", "169")

def main():
    # load chunks
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"Loaded {len(chunks)} chunks total\n")

    # filter to target episodes only
    chunks = [c for c in chunks if c["episode"] in TARGET_EPISODES]
    print(f"Filtered to {len(chunks)} chunks for episodes {TARGET_EPISODES}\n")

    # set up voyage client
    voyage = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

    # set up pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

    if PINECONE_INDEX not in pc.list_indexes().names():
        print("Creating Pinecone index...")
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=512,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
    index = pc.Index(PINECONE_INDEX)
    print("Connected to Pinecone index\n")

    # delete existing vectors for target episodes
    for ep in TARGET_EPISODES:
        ids_to_delete = [f"ep{ep}_chunk{i}" for i in range(500)]
        index.delete(ids=ids_to_delete)
        print(f"Deleted old vectors for episode {ep}")
    print()

    # embed and upsert in batches
    total = len(chunks)
    for batch_start in range(0, total, BATCH_SIZE):
        batch = chunks[batch_start: batch_start + BATCH_SIZE]
        texts = [c["text"] for c in batch]

        result = voyage.embed(texts, model=EMBEDDING_MODEL, input_type="document")
        embeddings = result.embeddings

        vectors = []
        for i, (chunk, embedding) in enumerate(zip(batch, embeddings)):
            vector_id = f"ep{chunk['episode']}_chunk{chunk['chunk_index']}"
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "episode": chunk["episode"],
                    "guest": chunk["guest"],
                    "text": chunk["text"]
                }
            })

        index.upsert(vectors=vectors)
        print(f"Upserted chunks {batch_start + 1}–{min(batch_start + BATCH_SIZE, total)} of {total}")

    print("\nDone! All chunks embedded and stored in Pinecone.")

if __name__ == "__main__":
    main()