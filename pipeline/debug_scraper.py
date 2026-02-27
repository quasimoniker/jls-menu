import fitz  # this is pymupdf
import os
import time


doc = fitz.open("C:\\Users\\JacobLemon-Strauss\\Documents\\Code\\off_menu\\data\\pdfs\\Ep_169_Ania_Magliano_–.pdf")
text = ""
for page in doc:
    text += page.get_text()
with open("C:\\Users\\JacobLemon-Strauss\\Documents\\Code\\off_menu\\data\\transcripts\\Ep_169_Ania_Magliano_–.txt", "w", encoding="utf-8") as f:
    f.write(text)