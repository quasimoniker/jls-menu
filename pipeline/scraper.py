import requests
from bs4 import BeautifulSoup
import fitz  # this is pymupdf
import os
import time

BASE_URL = "https://www.offmenupodcast.co.uk"
TRANSCRIPTS_URL = f"{BASE_URL}/transcripts"
PDF_DIR = "data/pdfs"
TEXT_DIR = "data/transcripts"

def setup_dirs():
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(TEXT_DIR, exist_ok=True)

def get_pdf_links():
    response = requests.get(TRANSCRIPTS_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    episodes = []
    for li in soup.find_all("li"):
        link = li.find("a", href=True)
        if link and link["href"].endswith(".pdf"):
            raw_text = li.get_text(" ", strip=True)
            # strip the "Download transcript" suffix
            label = raw_text.replace("Download transcript", "").strip()
            href = link["href"]
            # normalize relative URLs
            if href.startswith("/"):
                href = BASE_URL + href
            episodes.append({"label": label, "url": href})

    return episodes

def download_pdf(url, filepath):
    headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
    response = requests.get(url)
    response.raise_for_status()
    with open(filepath, "wb") as f:
        f.write(response.content)
  
def extract_text(pdf_path, txt_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)

def main():
    print("Script Started")
    setup_dirs()
    episodes = get_pdf_links()
    print(f"Found {len(episodes)} transcripts\n")

    for ep in episodes:
        # build a clean filename from the label, e.g. "Ep 306 Marian Keyes"
        safe_name = ep["label"].replace("/", "-").replace(" ", "_")
        pdf_path = os.path.join(PDF_DIR, f"{safe_name}.pdf")
        txt_path = os.path.join(TEXT_DIR, f"{safe_name}.txt")

        if os.path.exists(txt_path):
            print(f"Skipping (already done): {ep['label']}")
            continue

        print(f"Downloading: {ep['label']}")
        try:
            if not os.path.exists(pdf_path):
                download_pdf(ep["url"], pdf_path)
            download_pdf(ep["url"], pdf_path)
            extract_text(pdf_path, txt_path)
            print(f"  ✓ Saved text")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

        time.sleep(0.5)  # be polite to their server

if __name__ == "__main__":
    main()