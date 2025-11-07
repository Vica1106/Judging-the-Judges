import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

url = "https://en.wikipedia.org/wiki/Glossary_of_computer_science"

# Use a polite User-Agent so Wikipedia serves full content
headers = {
    "User-Agent": "GamingAgent/1.0 (https://github.com/; contact: vica031106@gmail.com)",
    "Accept-Language": "en-US,en;q=0.9",
}

resp = requests.get(url, headers=headers, timeout=20)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")

concepts = []

# Wikipedia glossary entries are <dl> blocks with sibling <dt> (term) then <dd> (definition)
root = soup.select_one("div.mw-parser-output") or soup
dls = root.find_all("dl")

for dl in dls:
    # Iterate only direct <dt> children and pair with the immediate following <dd>
    for dt in dl.find_all("dt", recursive=False):
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue
        term = dt.get_text(" ", strip=True)
        definition = dd.get_text(" ", strip=True)

        # Remove citation markers like [1], [2], etc.
        term = re.sub(r"\[[0-9]+\]", "", term).strip()
        definition = re.sub(r"\[[0-9]+\]", "", definition).strip()

        if term and definition:
            concepts.append({"term": term, "definition": definition})

print("✅ Found", len(concepts), "concepts")

df = pd.DataFrame(concepts)
df.to_csv("glossary_of_cs.csv", index=False, encoding="utf-8")
print("💾 Saved to glossary_of_cs.csv")
