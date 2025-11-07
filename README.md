# Judging-the-Judges
Judging the Judges: Using AI and Humans to Evaluate LLM Explanations

## Quick start: scrape a Wikipedia glossary to CSV

Use the script in 'data/getDataFromWiki.py' to fetch a glossary page from Wikipedia and save it as a CSV.

### 1) Install dependencies

'''bash
pip3 install requests beautifulsoup4 pandas
'''

### 2) Choose the glossary URL

Edit the 'url' variable near the top of 'data/getDataFromWiki.py' to the glossary you want:

'''python
url = "https://en.wikipedia.org/wiki/Glossary_of_computer_science"
'''

Examples you can use:
- 'https://en.wikipedia.org/wiki/Glossary_of_artificial_intelligence'
- 'https://en.wikipedia.org/wiki/Glossary_of_computer_science'
- 'https://en.wikipedia.org/wiki/Glossary_of_statistics'

Optional: change the output filename by editing the 'to_csv' line at the bottom of the script:

'''python
df.to_csv("glossary_of_cs.csv", index=False, encoding="utf-8")
'''

### 3) Run the scraper

Run from the 'data/' folder so the CSV is saved next to the script:

'''bash
cd data
python3 getDataFromWiki.py
'''

You should see a message like:

'''
✅ Found 300 concepts
💾 Saved to glossary_of_cs.csv
'''

The resulting file will be in 'data/' (e.g., 'data/glossary_of_cs.csv').

## Check concept difficulty with 'data_filter.py'

This script uses an LLM judge to score how difficult each concept is for non-majors and writes results to 'results.jsonl'.

### 1) Install judge dependencies

'''bash
pip3 install pandas python-dotenv langfuse openai
'''

### 2) Set your API keys in a '.env' file

Create a '.env' in the project root with at least your OpenAI key:

'''bash
echo "OPENAI_API_KEY=sk-..." > .env
'''

### 3) Get Score for each concept

Edit the inputs at the bottom of 'data_filter.py' to choose the major and CSV path, then run it:

Run:

'''bash
python3 data_filter.py
'''

This appends JSON lines to 'results.jsonl', one per concept (first few rows by default). Example entry:

'''json
{"Major":"Physics","Term":"Lagrangian","Specialization":8,"Complexity":9,"Familiarity":7,"Explainability":7,"Interdisciplinary_Reach":6,"Cognitive_Load":9,"Overall Assessment":"..."}
'''