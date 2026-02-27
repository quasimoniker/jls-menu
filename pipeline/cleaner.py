import os
import re

INPUT_DIR = "data/transcripts"
OUTPUT_DIR = "data/cleaned"

def setup_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def parse_filename(filename):
    # e.g. "Ep_306_Marian_Keyes.txt" -> {"episode": "306", "guest": "Marian Keyes"}
    name = filename.replace(".txt", "")
    parts = name.split("_")
    # first part is "Ep", second is the number, rest is the guest name
    episode = parts[1] if len(parts) > 1 else "unknown"
    guest = " ".join(parts[2:]).replace("-", "/")
    guest = guest.strip("–- ").strip()
    return {"episode": episode, "guest": guest}

def clean_text(text):
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # skip page numbers (lone digits)
        if re.fullmatch(r"\d+", stripped):
            continue
        if re.fullmatch(r"-\s*\d+\s*-", stripped):
            continue
        # skip copyright lines
        if stripped.startswith("© Plosive"):
            continue
        # skip header lines like "Off Menu – Ep 225: Susan Wokoma"
        if re.match(r"Off Menu\s*[–-]\s*Ep\s*\d+", stripped):
            continue
        # strip timestamps like "00:13" or "1:23:45" from end of line
        line = re.sub(r"\s+\d{1,2}:\d{2}(:\d{2})?\s*$", "", line)
        stripped = line.strip()  # re-strip since line changed
        cleaned.append(line)

    # collapse multiple blank lines into one
    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def main():
    setup_dirs()
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")]
    print(f"Found {len(files)} transcripts to clean\n")

    for filename in files:
        meta = parse_filename(filename)
        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)

        with open(input_path, "r", encoding="utf-8") as f:
            raw = f.read()

        cleaned = clean_text(raw)

        # prepend metadata header so we always know what episode this is
        header = f"EPISODE: {meta['episode']}\nGUEST: {meta['guest']}\n\n"
        final = header + cleaned

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final)

        print(f"Cleaned: Ep {meta['episode']} – {meta['guest']}")

    print("\nDone!")

if __name__ == "__main__":
    main()