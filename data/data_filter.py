
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
    Your task is to evaluate how difficult a given term from a specific academic major would be 
    for an average college student who is **not majoring in that field**, but who has taken some general education courses.

    For each input, you will receive:
    - **Major**: the academic field where the term belongs
    - **Term**: the word or phrase to be judged
    - **Explanation**: a short definition or contextual description (if provided)

    Please evaluate the term on the following dimensions, each rated from **1 to 10**, and return an number for each:

    1. **Specialization** - How exclusive is this term to the given major?  
    (1 = very common in everyday life, 10 = almost never seen outside this academic field)

    2. **Complexity** - How difficult is the concept to understand for someone without specialized training?  
    (1 = easily understood, 10 = requires advanced theoretical background or multiple sub-concepts)

    3. **Familiarity** - How likely is it that an average college student has heard this term before?  
    (1 = very likely, 10 = almost unknown to the general student population)

    4. **Explainability** - How easily can this concept be explained in one short, non-technical sentence?  
    (1 = very easy to explain simply, 10 = very hard to simplify without losing accuracy)

    5. **Interdisciplinary Reach** - How widely is this term used across multiple disciplines?  
    (1 = commonly used in several fields, 10 = only relevant in a single specialized subfield)

    6. **Cognitive Load** - How much abstract reasoning or technical background is required to understand the concept?  
    (1 = concrete and intuitive, 10 = highly abstract or mathematically demanding)

    Finally, provide a **short overall comment** summarizing whether this term would likely be difficult 
    for a non-major student to grasp quickly, based on your ratings.

    ### Output format (JSON preferred):
    {
    "Major": "...",
    "Term": "...",
    "Specialization": ,
    "Complexity": ,
    "Familiarity": ,
    "Explainability": ,
    "Interdisciplinary_Reach": ,
    "Cognitive_Load":,
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
            f.write(json.dumps(json.loads(result), ensure_ascii=False) + "\n")
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
   