import os
import json
import csv
import anthropic
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE = os.path.join(BASE_DIR, "data", "menu_choices.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "menu_choices_normalised.csv")
REVIEW_FILE = os.path.join(BASE_DIR, "data", "normalisation_review.json")

COLUMNS_TO_NORMALISE = ["starter", "main", "dessert", "drink"]

NORMALISE_PROMPT_PASS1 = """You are helping normalise menu choice descriptions from the Off Menu podcast into short canonical names.

For each item, return:
- "normalised": a short canonical name (2-4 words max) if it's a real, recognisable food or drink
- "normalised": the original text unchanged if it's surreal, impossible, or novelty
- "confidence": "high" if you're certain, "medium" if reasonable but could go either way, "low" if genuinely unclear

Rules:
- Real food: "vodka rigatoni from Bertie Blossoms" → "vodka rigatoni"
- Real food with details: "prawn cocktail with Marie Rose sauce" → "prawn cocktail"
- Surreal/impossible: "the smell of your own brain sizzling" → keep as-is
- Novelty but real food: "Greggs sausage roll" → "Greggs sausage roll" (brand is meaningful)
- Already short: "tiramisu" → "tiramisu"

Return a JSON array in exactly this format, one object per item, in the same order as input:
[
  {{"original": "...", "normalised": "...", "confidence": "high|medium|low"}},
  ...
]

Items to normalise:"""

NORMALISE_PROMPT_PASS2 = """You are helping reduce food and drink names to their core dish type for the Off Menu podcast dataset.

For each item, return:
- "normalised": the core dish name — specific enough to be meaningful but without restaurant names, brand names, or descriptive details
- "confidence": "high" if you're certain, "medium" if reasonable but could go either way, "low" if genuinely unclear

Rules:
- Remove brand/restaurant names: "Nino's pizza" → "pizza", "Franco Manca pizza" → "pizza"
- Keep at dish level, not ingredient level: "vodka rigatoni" → "pasta" is too broad, keep "rigatoni" or "pasta dish"
- Already at dish level: "tiramisu" → "tiramisu", "prawn cocktail" → "prawn cocktail"
- Surreal/impossible: keep unchanged
- If genuinely ambiguous: keep unchanged and mark as low confidence

Return a JSON array in exactly this format, one object per item, in the same order as input:
[
  {{"original": "...", "normalised": "...", "confidence": "high|medium|low"}},
  ...
]

Items to normalise:"""


def normalise_batch(values: list[str], prompt: str) -> list[dict]:
    """Send a batch of values to Claude for normalisation."""
    items_text = "\n".join(f"{i+1}. {v}" for i, v in enumerate(values))

    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": prompt + "\n\n" + items_text
        }]
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    return json.loads(text.strip())


def run_pass(df: pd.DataFrame, prompt: str, pass_name: str) -> tuple[pd.DataFrame, list[dict]]:
    """Run a normalisation pass over all target columns."""
    review_items = []
    BATCH_SIZE = 50

    for col in COLUMNS_TO_NORMALISE:
        print(f"\n  Normalising column: {col}")
        values = df[col].fillna("").tolist()
        to_process = [(i, v) for i, v in enumerate(values) if v.strip()]
        print(f"  {len(to_process)} non-empty values")

        results_by_index = {}

        for batch_start in range(0, len(to_process), BATCH_SIZE):
            batch = to_process[batch_start:batch_start + BATCH_SIZE]
            batch_values = [v for _, v in batch]
            batch_indices = [i for i, _ in batch]

            print(f"  Processing items {batch_start + 1}–{min(batch_start + BATCH_SIZE, len(to_process))}...")

            try:
                results = normalise_batch(batch_values, prompt)
                for idx, result in zip(batch_indices, results):
                    results_by_index[idx] = result
                    if result["confidence"] in ("low", "medium"):
                        review_items.append({
                            "pass": pass_name,
                            "column": col,
                            "row_index": idx,
                            "guest": df.iloc[idx]["guest"],
                            "original": result["original"],
                            "normalised": result["normalised"],
                            "confidence": result["confidence"]
                        })
            except Exception as e:
                import traceback
                traceback.print_exc()
                for idx, val in zip(batch_indices, batch_values):
                    results_by_index[idx] = {
                        "original": val,
                        "normalised": val,
                        "confidence": "low"
                    }

        for i, val in enumerate(values):
            if i in results_by_index:
                df.at[i, col] = results_by_index[i]["normalised"]

    return df, review_items


def main():
    df = pd.read_csv(INPUT_FILE)
    df.columns = df.columns.str.strip().str.lower()
    df["guest"] = df["guest"].str.replace(r"[/\\]+$", "", regex=True).str.strip()

    print("=== Pass 1: Removing descriptions and restaurant names ===")
    df, review_pass1 = run_pass(df, NORMALISE_PROMPT_PASS1, "pass1")

    print("\n=== Pass 2: Reducing to core dish type ===")
    df, review_pass2 = run_pass(df, NORMALISE_PROMPT_PASS2, "pass2")

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved normalised CSV to {OUTPUT_FILE}")

    all_review = review_pass1 + review_pass2
    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        json.dump(all_review, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(all_review)} items for review to {REVIEW_FILE}")
    print("\nDone!")


if __name__ == "__main__":
    main()