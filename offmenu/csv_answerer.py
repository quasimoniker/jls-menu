import os
import pandas as pd
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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_FILE = os.path.join(BASE_DIR, "data", "menu_choices.csv")
CSV_NORMALISED_FILE = os.path.join(BASE_DIR, "data", "menu_choices_normalised.csv")

MENU_COLUMNS = ["starter", "main", "dessert", "drink", "still_or_sparkling", "poppadoms_or_bread"]
CHRISTMAS_COLUMN = "christmas_dinner"
ALL_CHOICE_COLUMNS = MENU_COLUMNS + [CHRISTMAS_COLUMN]

SYSTEM_PROMPT = """You are a knowledgeable assistant for the Off Menu podcast, hosted by Ed Gamble and James Acaster.
You have been provided with structured data about guests' menu choices. Answer the question naturally and conversationally based on this data.
If the data doesn't contain enough information to answer, say so clearly."""


def load_csvs() -> tuple[pd.DataFrame, pd.DataFrame]:
    def clean(df):
        df.columns = df.columns.str.strip().str.lower()
        df["guest"] = df["guest"].str.replace(r"[/\\]+$", "", regex=True).str.strip()
        return df

    df_raw = clean(pd.read_csv(CSV_FILE))
    df_norm = clean(pd.read_csv(CSV_NORMALISED_FILE))
    return df_raw, df_norm


def find_guest_match(question: str, df: pd.DataFrame) -> str | None:
    q = question.lower()
    for guest in df["guest"]:
        clean = str(guest).lower().replace("/", " ").replace("-", " ")
        if clean in q:
            return guest
        parts = str(guest).split()
        if len(parts) >= 2 and parts[0].lower() in q and parts[-1].lower() in q:
            return guest
    return None


def find_target_column(question: str) -> str | None:
    keyword_map = {
        "starter": "starter",
        "main": "main",
        "dessert": "dessert",
        "pudding": "dessert",
        "drink": "drink",
        "beverage": "drink",
        "still": "still_or_sparkling",
        "sparkling": "still_or_sparkling",
        "water": "still_or_sparkling",
        "poppadom": "poppadoms_or_bread",
        "bread": "poppadoms_or_bread",
        "christmas": "christmas_dinner",
    }
    q = question.lower()
    for keyword, col in keyword_map.items():
        if keyword in q:
            return col
    return None


def search_value_across_columns(search_term: str, df: pd.DataFrame) -> dict:
    results = {}
    term = search_term.lower()
    for col in ALL_CHOICE_COLUMNS:
        col_data = df[["guest", col]].dropna()
        if col == CHRISTMAS_COLUMN:
            col_data = col_data[col_data[col].str.strip() != ""]
        matches = col_data[col_data[col].str.lower().str.contains(term, na=False)]
        if not matches.empty:
            results[col] = list(zip(matches["guest"], matches[col]))
    return results


def extract_search_terms(question: str) -> list[str]:
    stopwords = {
        "what", "which", "who", "has", "have", "ever", "chosen", "chose",
        "picked", "pick", "anyone", "a", "an", "the", "their", "as", "is",
        "are", "did", "does", "most", "common", "popular", "guests", "guest",
        "main", "starter", "dessert", "drink", "course", "for", "on", "menu",
        "off", "podcast", "episode", "how", "many", "times", "been", "any"
    }
    words = question.lower().replace("?", "").replace("'", "").split()
    return [w for w in words if w not in stopwords and len(w) > 2]


def build_csv_context(question: str, df_raw: pd.DataFrame, df_norm: pd.DataFrame) -> str:
    lines = []
    q = question.lower()

    # --- PATH 1: Guest-specific lookup (use raw for full descriptive answer) ---
    guest_match = find_guest_match(question, df_raw)
    if guest_match:
        row = df_raw[df_raw["guest"] == guest_match]
        if row.empty:
            return f"No data found for guest: {guest_match}"
        row = row.iloc[0]
        lines.append(f"Menu choices for {guest_match} (Episode {row.get('episode', 'unknown')}):")
        for col in MENU_COLUMNS:
            val = row.get(col)
            if pd.notna(val) and str(val).strip():
                lines.append(f"  {col}: {val}")
        christmas = row.get(CHRISTMAS_COLUMN)
        if pd.notna(christmas) and str(christmas).strip():
            lines.append(f"  christmas_dinner: {christmas}")
        return "\n".join(lines)

    # --- PATH 2: Aggregation over a specific column (use normalised) ---
    aggregation_keywords = ["most common", "most popular", "how many", "which guests",
                            "who chose", "who picked", "everyone who", "all guests"]
    is_aggregation = any(kw in q for kw in aggregation_keywords)
    target_col = find_target_column(question)

    if is_aggregation and target_col:
        col_data = df_norm[["guest", target_col]].dropna()
        if target_col == CHRISTMAS_COLUMN:
            col_data = col_data[col_data[target_col].str.strip() != ""]

        counts = col_data[target_col].value_counts()
        lines.append(f"Value counts for '{target_col}' across {len(col_data)} guests:")
        for value, count in counts.items():
            lines.append(f"  {value}: {count}")
        return "\n".join(lines)

    # --- PATH 3: Value search across all columns (use normalised) ---
    search_terms = extract_search_terms(question)
    if search_terms:
        all_results = {}
        # try pairs of adjacent terms first
        for i in range(len(search_terms) - 1):
            phrase = f"{search_terms[i]} {search_terms[i+1]}"
            results = search_value_across_columns(phrase, df_norm)
            if results:
                all_results.update(results)
        # fall back to individual terms
        if not all_results:
            for term in search_terms:
                results = search_value_across_columns(term, df_norm)
                all_results.update(results)

        if all_results:
            lines.append(f"Search results for question: '{question}'")
            for col, matches in all_results.items():
                lines.append(f"\nMatches in '{col}':")
                for guest, value in matches:
                    lines.append(f"  {guest}: {value}")
            return "\n".join(lines)
        else:
            return f"No matches found across any menu column for the terms in: '{question}'"

    # --- FALLBACK ---
    lines.append(f"Total guests in dataset: {len(df_norm)}")
    lines.append("\nTop 5 most common choices per column:")
    for col in MENU_COLUMNS:
        counts = df_norm[col].dropna().value_counts().head(5)
        lines.append(f"\n{col}:")
        for value, count in counts.items():
            lines.append(f"  {value}: {count}")
    return "\n".join(lines)


def answer_from_csv(question: str) -> str:
    df_raw, df_norm = load_csvs()
    context = build_csv_context(question, df_raw, df_norm)

    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": f"{SYSTEM_PROMPT}\n\nData:\n{context}\n\nQuestion: {question}"
        }]
    )
    return response.content[0].text