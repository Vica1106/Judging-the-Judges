
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()
from langfuse.openai import openai
import os
import json
import argparse
import sys

def LLM_Judge(major: str, word: str):
    #Create a chat completion using Langfuse-integrated OpenAI client
    system_prompt = """
    Explain the major term for me as short as possible.
    """
    completion = openai.chat.completions.create(
        name="explain-chat",
        model="gpt-5-nano-2025-08-07",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": major + "\n\nTerm: " + word}
        ],
        metadata={"task": "explaining"}
    )
    # print(completion)
    return completion.choices[0].message.content

def calculate_average_score(entry):
    """Calculate average score from the 6 dimensions"""
    scores = [
        entry.get("Specialization", 0),
        entry.get("Complexity", 0),
        entry.get("Familiarity", 0),
        entry.get("Explainability", 0),
        entry.get("Interdisciplinary_Reach", 0),
        entry.get("Cognitive_Load", 0)
    ]
    return sum(scores) / len(scores) if scores else 0

def generate_top_k_filename(input_path: str, top_n: int):
    """Generate output filename based on input filename"""
    base_name = os.path.splitext(input_path)[0]  # Remove .jsonl extension
    return f"judged_dataset/{base_name}_top{top_n}.jsonl"

def process_jsonl_to_explanations(jsonl_path: str, output_path: str, top_n: int = 10):
    """Read JSONL results, find top N by average score, and generate explanations"""
    top_k_filename = generate_top_k_filename(jsonl_path, top_n)
    top_entries = []
    
    # Check if top k file already exists
    if os.path.exists(top_k_filename):
        print(f"✅ Found existing top {top_n} file: {top_k_filename}")
        print("Using existing file instead of re-running selection process...")
        print("")
        
        # Read top entries from existing file
        with open(top_k_filename, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    top_entries.append(json.loads(line.strip()))
        
        if not top_entries:
            print(f"Warning: Top k file exists but is empty. Re-running selection process...")
        else:
            print(f"Loaded {len(top_entries)} entries from existing file.")
            print("")
    
    # If top_entries is still empty (file didn't exist or was empty), run selection
    if not top_entries:
        # Read all entries from JSONL file and select top k
        print(f"Top k file not found. Running selection process...")
        entries = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line.strip()))
        
        if not entries:
            print(f"Error: No entries found in {jsonl_path}")
            return
        
        # Calculate average scores and sort
        scored_entries = []
        for entry in entries:
            avg_score = calculate_average_score(entry)
            scored_entries.append((entry, avg_score))
        
        # Sort by average score (descending) and get top N
        scored_entries.sort(key=lambda x: x[1], reverse=True)
        top_entries = [entry for entry, score in scored_entries[:top_n]]
        
        print(f"Found {len(entries)} entries. Selected top {top_n} by average score...")
        print("")
        
        # Save top k entries to a new file
        # Ensure data directory exists
        os.makedirs(os.path.dirname(top_k_filename), exist_ok=True)
        
        with open(top_k_filename, "w", encoding="utf-8") as f:
            for entry in top_entries:
                # Add average score to the entry
                entry_with_avg = entry.copy()
                entry_with_avg["Average_Score"] = round(calculate_average_score(entry), 2)
                f.write(json.dumps(entry_with_avg, ensure_ascii=False) + "\n")
        print(f"✅ Saved top {top_n} entries to: {top_k_filename}")
        print("")
    
    # Get major from first entry
    major = top_entries[0].get("Major", "")
    
    # Generate explanations for top entries
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in top_entries:
            term = entry.get("Term", "")
            result = LLM_Judge(major, term)
            
            # Create output entry with explanation
            output_entry = {
                "Major": major,
                "Term": term,
                "Explanation": result
            }
            
            f.write(json.dumps(output_entry, ensure_ascii=False) + "\n")
            print(f"✅ Processed: {term}")
            print("")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process JSONL results and generate explanations for top N terms")
    parser.add_argument("--input", type=str, default="judged_dataset/glossary_of_AI_results.jsonl", help="Path to input JSONL file from data_filter.py")
    parser.add_argument("--output", type=str, default="response_dataset/top_explanations_AI.jsonl", help="Path to output JSONL file (default: top_explanations.jsonl)")
    parser.add_argument("--top", type=int, default=10, help="Number of top terms to process (default: 10)")
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found.")
        sys.exit(1)
    
    process_jsonl_to_explanations(args.input, args.output, args.top)
   