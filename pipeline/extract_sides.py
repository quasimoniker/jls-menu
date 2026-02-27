import os
import json
import csv
import anthropic as anthropic_lib
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

anthropic = anthropic_lib.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, "data", "cleaned")
CSV_FILE = os.path.join(BASE_DIR, "data", "menu_choices.csv")
CSV_NORM_FILE = os.path.join(BASE_DIR, "data", "menu_choices_normalised.csv")

PROMPT = """You are extracting structured data from an Off Menu podcast transcript.
Off Menu is a podcast where Ed Gamble and James Acaster ask guests to describe their perfect dream meal in a magical restaurant.
As part of the meal, guests choose a side dish to accompany their main course. It may be referred to as "side dish" or just "side".

Extract the guest's final side dish choice from the transcript below.
Return ONLY a JSON object with one key: side_dish.
If no side dish was chosen or mentioned, use null.
If the guest was indecisive or chose multiple things, list them all as a single string.
Do not include any explanation or text outside the JSON object.

TRANSCRIPT:
{transcript}"""


def extract_side(transcript):
    response = anthropic.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=128,
        messages=[{"role": "user", "content": PROMPT.format(transcript=transcript)}]
    )
    raw = response.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    result = json.loads(raw)
    return result.get("side_dish")


def parse_metadata(text):
    episode, guest = "unknown", "unknown"
    for line in text.split("\n"):
        if line.startswith("EPISODE:"):
            episode = line.replace("EPISODE:", "").strip()
        elif line.startswith("GUEST:"):
            guest = line.replace("GUEST:", "").strip()
    return episode, guest


def main():
    # load existing CSVs
    df_raw = pd.read_csv(CSV_FILE)
    df_norm = pd.read_csv(CSV_NORM_FILE)

    # add side_dish column if not present
    if "side_dish" not in df_raw.columns:
        df_raw["side_dish"] = None
    if "side_dish" not in df_norm.columns:
        df_norm["side_dish"] = None

    files = sorted(os.listdir(INPUT_DIR))
    total = len(files)

    for i, filename in enumerate(files):
        if not filename.endswith(".txt"):
            continue

        path = os.path.join(INPUT_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        episode, guest = parse_metadata(text)

        # find matching row
        mask = df_raw["episode"].astype(str) == str(episode)
        if not mask.any():
            print(f"Skipping (not in CSV): Ep {episode} – {guest}")
            continue

        print(f"[{i+1}/{total}] Extracting side dish: Ep {episode} – {guest}")
        try:
            side = extract_side(text)
            df_raw.loc[mask, "side_dish"] = side
            df_norm.loc[mask, "side_dish"] = side  # raw value for now, normalise separately
            print(f"  ✓ {side}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

    # save both CSVs
    df_raw.to_csv(CSV_FILE, index=False)
    df_norm.to_csv(CSV_NORM_FILE, index=False)
    print("\nDone! Both CSVs updated with side_dish column.")


if __name__ == "__main__":
    main()