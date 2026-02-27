import os
import json
import csv
import time
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

INPUT_DIR = "data/cleaned"
OUTPUT_FILE = "data/menu_choices.csv"

anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

COLUMNS = [
    "episode", "guest", "starter", "main", "dessert",
    "drink", "still_or_sparkling", "poppadoms_or_bread", "christmas_dinner"
]

PROMPT_TEMPLATE = """You are extracting structured data from an Off Menu podcast transcript.
Off Menu is a podcast where Ed Gamble and James Acaster ask guests to describe their perfect dream meal in a magical restaurant. 
The guests choose: a drink, still or sparkling water, poppadoms or bread, a starter, a main course, a dessert, and optionally a christmas dinner (christmas special episodes only).

Extract the guest's final choices for each category from the transcript below.
Return ONLY a JSON object with these exact keys: starter, main, dessert, drink, still_or_sparkling, poppadoms_or_bread, christmas_dinner.
If a category was not chosen or not mentioned, use null.
If the guest was indecisive or chose multiple things, list them all as a single string.
Do not include any explanation or text outside the JSON object.

TRANSCRIPT:
{transcript}"""

def extract_choices(transcript, episode, guest):
    prompt = PROMPT_TEMPLATE.format(transcript=transcript)
    
    response = anthropic.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw = response.content[0].text.strip()
    # strip markdown code fences if claude returns them
    raw = raw.replace("```json", "").replace("```", "").strip()
    choices = json.loads(raw)
    choices["episode"] = episode
    choices["guest"] = guest
    return choices

def parse_metadata(text):
    episode, guest = "unknown", "unknown"
    for line in text.split("\n"):
        if line.startswith("EPISODE:"):
            episode = line.replace("EPISODE:", "").strip()
        elif line.startswith("GUEST:"):
            guest = line.replace("GUEST:", "").strip()
    return episode, guest

def load_processed_episodes():
    processed = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed.add(row["episode"])
    return processed

def main():
    files = sorted([f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")])
    print(f"Found {len(files)} transcripts\n")

    # load already processed episodes so we can resume if interrupted
    processed = load_processed_episodes()
    print(f"Already processed: {len(processed)} episodes\n")

    # open csv in append mode so we don't overwrite existing results
    file_exists = os.path.exists(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        print(f"CSV opened at: {os.path.abspath(OUTPUT_FILE)}")
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        
        # only write header if file is new
        if not file_exists:
            writer.writeheader()

        for filename in files:
            path = os.path.join(INPUT_DIR, filename)
            with open(path, "r", encoding="utf-8") as tf:
                text = tf.read()

            episode, guest = parse_metadata(text)

            if episode in processed:
                print(f"Skipping (already done): Ep {episode} – {guest}")
                continue

            print(f"Extracting: Ep {episode} – {guest}")
            try:
                choices = extract_choices(text, episode, guest)
                writer.writerow(choices)
                f.flush()  # write to disk immediately in case of interruption
                print(f"  ✓ Done")
            except Exception as e:
                print(f"  ✗ Failed: {e}")

            time.sleep(0.5)

    print(f"\nDone! Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()