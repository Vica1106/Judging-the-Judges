
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()
from langfuse.openai import openai
import os
import pandas as pd
import json
import argparse
import sys

def LLM_Judge(major: str, term: str, explanation: str = None):
    #Create a chat completion using Langfuse-integrated OpenAI client
    system_prompt = """
    You are an expert in interdisciplinary education and language complexity analysis.
    For each input, return:
    - Major (string)
    - Term (string)
    - Complexity (integer 1–10): difficulty for a non-major to understand (1 = easy, 10 = hardest)
    - Familiarity (integer 1–10): how likely an average student has heard the term (1 = very likely/common, 10 = almost unknown)
    - Explainability (integer 1–10): how easy it is to explain simply (1 = very easy to explain, 10 = very hard to simplify)
    - Overall Assessment (short comment)

    Output strictly as compact JSON with exactly these fields and no extras:
    {
      "Major": "...",
      "Term": "...",
      "Complexity": ,
      "Familiarity": ,
      "Explainability": ,
      "Overall Assessment": "..."
    }
    """
    completion = openai.chat.completions.create(
        name="judge-chat",
        model="gpt-5-nano-2025-08-07",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": major + "\n\nTerm: " + term + (f"\n\nExplanation: {explanation}" if explanation else "")}
        ],
        metadata={"task": "judging"}
    )
    # print(completion)
    return completion.choices[0].message.content

def get_processed_terms(output_path: str):
    """Read existing output file and return set of already processed terms"""
    processed_terms = set()
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line.strip())
                        term = entry.get("Term", "")
                        if term:
                            processed_terms.add(term)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read existing output file: {e}")
    return processed_terms

def process_csv_to_jsonl(major:str, csv_path: str, output_path: str):
    df = pd.read_csv(csv_path)
    
    # Get already processed terms
    processed_terms = get_processed_terms(output_path)
    if processed_terms:
        print(f"Found {len(processed_terms)} already processed terms. Skipping those...")
    
    total_rows = len(df)
    skipped_count = 0
    processed_count = 0
    
    with open(output_path, "a", encoding="utf-8") as f:
        for _, row in df.iterrows():
            term = row.get("term", "")
            explanation = row.get("definition", None)
            
            # Skip if already processed
            if term in processed_terms:
                skipped_count += 1
                print(f"⏭️  Skipped (already processed): {term}")
                continue

            result = LLM_Judge(major, term, explanation)
            try:
                parsed = json.loads(result)
                # Ensure required fields present and normalized
                def to_int_safe(v):
                    try:
                        return int(v)
                    except (TypeError, ValueError):
                        try:
                            return int(float(v))
                        except (TypeError, ValueError):
                            return None

                filtered = {
                    "Major": parsed.get("Major") or major,
                    "Term": parsed.get("Term") or term,
                    "Complexity": to_int_safe(parsed.get("Complexity")),
                    "Familiarity": to_int_safe(parsed.get("Familiarity")),
                    "Explainability": to_int_safe(parsed.get("Explainability")),
                    "Overall Assessment": parsed.get("Overall Assessment") or "",
                }
            except json.JSONDecodeError:
                # Fallback: write a minimal placeholder if parsing fails
                filtered = {
                    "Major": major,
                    "Term": term,
                    "Complexity": None,
                    "Familiarity": None,
                    "Explainability": None,
                    "Overall Assessment": "",
                }

            f.write(json.dumps(filtered, ensure_ascii=False) + "\n")
            print(f"✅ Processed: {term}")
            processed_count += 1
    
    print(f"\nSummary: {processed_count} new entries processed, {skipped_count} skipped, {total_rows} total in CSV")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process CSV files and generate JSONL output with LLM judgments")
    parser.add_argument("--major", type=str, required=True, help="Academic major name (e.g., 'Physics', 'AI', 'Computer Science')")
    parser.add_argument("--input", type=str, required=True, help="Path to input CSV file")
    parser.add_argument("--output", type=str, default="results.jsonl", help="Path to output JSONL file (default: results.jsonl)")
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found.")
        sys.exit(1)
    
    process_csv_to_jsonl(args.major, args.input, args.output)
   