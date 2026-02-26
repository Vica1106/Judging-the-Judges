# Judging-the-Judges
Judging the Judges: Using AI and Humans to Evaluate LLM Explanations

## Installation

### Dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

**Key dependencies:**
- `python-dotenv` - Environment variable management
- `langfuse` - LLM observability and tracing
- `openai` - OpenAI API client
- `pandas` - Data processing and manipulation
- `requests` & `beautifulsoup4` - Web scraping for Wikipedia glossaries
- `numpy`, `matplotlib`, `seaborn`, `scikit-learn` - Data analysis and visualization (for notebooks)

### Setup

1. Create a `.env` file in the project root with your API keys:
   ```bash
   OPENAI_API_KEY=sk-...
   LANGFUSE_PUBLIC_KEY=...
   LANGFUSE_SECRET_KEY=...
   ```

2. Ensure prompt files are in the `prompts/` directory
3. Place CSV files to process in `data/raw_data/`

## Project Structure

```
Judging-the-Judges/
├── analyze/                          # Analysis scripts and notebooks
│   ├── analyze_evaluation.py        # Calculate Elo ratings from evaluation results
│   ├── evaluate_explanations.py     # Pairwise comparison of explanations
│   ├── analysis.ipynb                # Analysis notebook
│   └── Jessie_da.ipynb              # Data analysis notebook
├── data/
│   ├── data_filter.py               # Judge concept difficulty using LLM
│   ├── response_generator.py        # Generate explanations using different prompts
│   ├── judged_dataset/              # Output: judged concept difficulty scores
│   ├── raw_data/                    # Input: CSV files with glossary terms
│   │   └── getDataFromWiki.py      # Scrape Wikipedia glossaries to CSV
│   └── response_dataset/            # Output: generated explanations per prompt variant
├── prompts/                         # Prompt templates
│   ├── baseline.json                # Baseline prompt template
│   ├── level2_multi_aspect.json    # Multi-aspect prompt template
│   ├── round2/                      # Refined Round2 prompt templates
│   └── prompt_round2.py             # Generate Round2 prompts from feedback
├── result/                          # Evaluation results
│   ├── evaluation_results.jsonl     # Pairwise comparison results
│   ├── elo_ratings.json            # Final Elo rankings
│   └── human_eval_rankings.json    # Human evaluation rankings
├── process_all_csv.sh               # Process all CSVs and generate responses
├── run_evaluation.sh                # Run pairwise evaluation and Elo calculation
├── generate_r2_responses.sh         # Generate Round2 explanations
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## Quick start: Run the full pipeline with shell scripts

You can run the entire pipeline with two commands from the repo root:

```bash
# 1) Build judged and response datasets for all CSVs in data/raw_data/
bash process_all_csv.sh

# 2) Evaluate all generated explanations and compute Elo ratings
bash run_evaluation.sh
```

What happens:
- Judged outputs are written to `data/judged_dataset/*.jsonl`
- Explanations are generated for three prompt variants and saved under:
  - `data/response_dataset/<prompt_name>/`
- Pairwise evaluation results go to `result/evaluation_results.jsonl`
- Elo rankings go to `result/elo_ratings.json`

**Prerequisites:**
- Python dependencies installed (see [Installation](#installation) section above)
- A `.env` file with your API keys (e.g., `OPENAI_API_KEY=...`)
- Prompt files in `prompts/` (e.g., `baseline.json`, `level2_multi_aspect.json`, `level3_multi_perspective.json`, `5_step.json`)
- CSVs to process in `data/raw_data/` (e.g., `glossary_of_AI.csv`, `glossary_of_cs.csv`, `glossary_of_stats.csv`)

## Scrape a Wikipedia glossary to CSV

Use the script in `data/raw_data/getDataFromWiki.py` to fetch a glossary page from Wikipedia and save it as a CSV.

### 1) Install dependencies

If you haven't already, install dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

Or install just the scraping dependencies:

```bash
pip3 install requests beautifulsoup4 pandas
```

### 2) Choose the glossary URL

Edit the `url` variable near the top of `data/raw_data/getDataFromWiki.py` to the glossary you want:

```python
url = "https://en.wikipedia.org/wiki/Glossary_of_computer_science"
```

Examples you can use:
- 'https://en.wikipedia.org/wiki/Glossary_of_artificial_intelligence'
- 'https://en.wikipedia.org/wiki/Glossary_of_computer_science'
- 'https://en.wikipedia.org/wiki/Glossary_of_statistics'

Optional: change the output filename by editing the `to_csv` line at the bottom of the script:

```python
df.to_csv("glossary_of_cs.csv", index=False, encoding="utf-8")
```

### 3) Run the scraper

Run from the `data/raw_data/` folder so the CSV is saved next to the script:

```bash
cd data/raw_data
python3 getDataFromWiki.py
```

You should see a message like:

```
✅ Found 300 concepts
💾 Saved to glossary_of_cs.csv
```

The resulting file will be in `data/raw_data/` (e.g., `data/raw_data/glossary_of_cs.csv`).

## Check concept difficulty with `data_filter.py`

This script uses an LLM judge to score how difficult each concept is for non-majors and writes results to `data/judged_dataset/*_results.jsonl`.

### 1) Install judge dependencies

All dependencies are included in `requirements.txt`. Install with:

```bash
pip install -r requirements.txt
```

### 2) Set your API keys in a '.env' file

Create a `.env` file in the project root with at least your OpenAI key:

```bash
echo "OPENAI_API_KEY=sk-..." > .env
```

### 3) Get Score for each concept

Edit the inputs at the bottom of `data/data_filter.py` to choose the major and CSV path, or use command-line arguments:

Run:

```bash
python3 data/data_filter.py --major "Computer Science" --input data/raw_data/glossary_of_cs.csv --output data/judged_dataset/glossary_of_cs_results.jsonl
```

This writes JSON lines to the output file, one per concept. Example entry:

```json
{"Major":"Physics","Term":"Lagrangian","Specialization":8,"Complexity":9,"Familiarity":7,"Explainability":7,"Interdisciplinary_Reach":6,"Cognitive_Load":9,"Overall Assessment":"..."}
```

## Generate Explanations with Different Prompts

After judging concepts, you can generate explanations using different prompt strategies.

### 1) Generate Explanations

Use `response_generator.py` to generate explanations for the top-k most difficult terms using different prompt templates.

**Setup:**
- Ensure you have prompt files in the `prompts/` folder (e.g., `baseline.json`, `level2_multi_aspect.json`, `level3_multi_perspective.json`)
- Each prompt file should contain a JSON with a `"prompt"` key or be a plain text file

**Run:**
```bash
python data/response_generator.py --input data/judged_dataset/glossary_of_AI_results_top10.jsonl --prompt-file prompts/baseline.json --output data/response_dataset/baseline/glossary_of_AI_explanations.jsonl
```

**What it does:**
- Reads the top-k terms from the judged dataset
- Generates explanations using the specified prompt template
- Saves results to `data/response_dataset/` with filenames like `top_explanations_AI__baseline.jsonl`

**Output format:**
Each JSONL entry contains:
- `Major`: The academic field
- `Term`: The concept being explained
- `Explanation`: The generated explanation text

**Features:**
- Automatically saves top-k entries to a separate file (e.g., `glossary_of_AI_results_top10.jsonl`)
- Skips already processed terms if you re-run
- Uses existing top-k file if available (avoids re-selection)

## Evaluate Explanations with Pairwise Comparison

Compare explanations generated from different prompts to determine which performs best.

### 1) Run Pairwise Evaluation

The evaluation system automatically finds all JSONL files in `data/response_dataset/` and performs pairwise comparisons.

**Run the complete pipeline:**
```bash
bash run_evaluation.sh
```

Or run manually:
```bash
# Step 1: Run pairwise evaluation
python analyze/evaluate_explanations.py --output result/evaluation_results.jsonl

# Step 2: Analyze results and calculate Elo ratings
python analyze/analyze_evaluation.py --input result/evaluation_results.jsonl --output result/elo_ratings.json
```

**What it does:**

1. **Pairwise Evaluation (`evaluate_explanations.py`):**
   - Automatically discovers all JSONL files in `data/response_dataset/`
   - For each term, compares all pairs of prompts (e.g., baseline vs level2, baseline vs level3, level2 vs level3)
   - Each comparison is judged **twice** (in both orders: A→B and B→A) to reduce order bias
   - Combines judgments: if both agree on a winner, that's the result; otherwise, it's a tie
   - Retries up to 3 times if a judgment returns "error"
   - Skips already processed comparisons if you re-run

2. **Analysis & Elo Ratings (`analyze_evaluation.py`):**
   - Analyzes all comparison results
   - Calculates Elo ratings for each prompt based on win/loss/tie records
   - Generates a ranking sorted by Elo score (descending)
   - Provides detailed statistics

**Output files:**

1. **`result/evaluation_results.jsonl`** - Detailed comparison results:
   - Each line contains a comparison between two prompts for one term
   - Includes both individual judgments (A→B and B→A orders)
   - Contains the combined winner, reasoning, strengths, and weaknesses
   - Example structure:
   ```json
   {
     "Term": "NP-completeness",
     "Major": "Artificial Intelligence",
     "Comparison": "baseline vs level2_multi_aspect",
     "Prompt_A": "baseline",
     "Prompt_B": "level2_multi_aspect",
     "Winner": "B",
     "Judgment_AB": {...},
     "Judgment_BA": {...},
     "Reasoning": "Combined from (baseline,level2_multi_aspect): B, (level2_multi_aspect,baseline): A"
   }
   ```

2. **`result/elo_ratings.json`** - Final rankings:
   ```json
   {
     "elo_ratings": {
       "baseline": 1502.69,
       "level2_multi_aspect": 1689.43,
       "level3_multi_perspective": 1307.88
     },
     "ranking": [
       {
         "rank": 1,
         "Prompt": "level2_multi_aspect",
         "elo": 1689.43
       },
       {
         "rank": 2,
         "Prompt": "baseline",
         "elo": 1502.69
       },
       {
         "rank": 3,
         "Prompt": "level3_multi_perspective",
         "elo": 1307.88
       }
     ]
   }
   ```

**Key Features:**

- **Order Swapping**: Each pair is judged in both orders (A→B and B→A) to eliminate position bias
- **Combined Results**: Only declares a winner if both judgments agree; otherwise results in a tie
- **Retry Logic**: Automatically retries up to 3 times if a judgment returns "error"
- **Resume Capability**: Skips already processed comparisons, so you can safely re-run
- **Elo Rating System**: Uses chess-style Elo ratings to rank prompts based on pairwise performance

**Understanding the Results:**

- **Elo Ratings**: Higher Elo = better performance. Ratings start at 1500 and adjust based on wins/losses
- **Ranking**: Sorted by Elo score (descending), showing which prompt generates the best explanations
- **Winner Logic**: 
  - If both (A→B) and (B→A) judgments agree → clear winner
  - If they disagree → tie (more conservative, reduces bias)

**Statistics Provided:**

- Win/loss/tie counts per comparison type
- Overall prompt performance (wins, losses, ties, win rate)
- Terms with most disagreements
- Elo ratings and final ranking

## Round2 Prompt Optimization

In addition to the base pipeline, we introduce a second refinement cycle that leverages judge feedback from the first evaluation round to improve prompt design.

The round2 process follows this loop:

1. Generate explanations using base prompts
2. Run pairwise evaluation and collect judge feedback
3. Identify recurring weaknesses and structural issues
4. Refine prompt instructions
5. Regenerate explanations and re-evaluate 

This transforms the pipeline from a single-pass evaluation into an iterative prompt optimization framework.

---

### 1) Generate Round2 Explanations

Run:

```bash
bash generate_r2_responses.sh
```

This script uses refined prompt templates (e.g., *_round2), generates new explanations, and ultimately saves outputs to `data/response_dataset/<prompt_name>_round2/`.

### 2) Re-run Evaluation

After generating Round2 explanations, run:

```bash
bash run_evaluation.sh
```

The evaluation system automatically detects all prompt variants (including Round1 and Round2), performs full pairwise comparisons, and updates Elo rankings accordingly.