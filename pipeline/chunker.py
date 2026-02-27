import os
import json

INPUT_DIR = "data/cleaned"
OUTPUT_FILE = "data/chunks.json"

CHUNK_SIZE = 500
OVERLAP = 100

def parse_metadata(text):
    lines = text.split("\n")
    episode, guest = "unknown", "unknown"
    for line in lines:
        if line.startswith("EPISODE:"):
            episode = line.replace("EPISODE:", "").strip()
        elif line.startswith("GUEST:"):
            guest = line.replace("GUEST:", "").strip()
    return episode, guest

def remove_metadata_header(text):
    # the metadata header is the first two lines, skip them
    lines = text.split("\n")
    # find the first blank line after the header and return everything after
    for i, line in enumerate(lines):
        if line.strip() == "" and i > 0:
            return "\n".join(lines[i:]).strip()
    return text

def chunk_text(text, chunk_size, overlap):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def main():
    os.makedirs("data", exist_ok=True)
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")]
    print(f"Found {len(files)} cleaned transcripts\n")

    all_chunks = []
    for filename in files:
        path = os.path.join(INPUT_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        episode, guest = parse_metadata(text)
        body = remove_metadata_header(text)
        chunks = chunk_text(body, CHUNK_SIZE, OVERLAP)

        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "episode": episode,
                "guest": guest,
                "chunk_index": i,
                "text": chunk
            })

        print(f"Ep {episode} – {guest}: {len(chunks)} chunks")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"\nTotal chunks: {len(all_chunks)}")
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()