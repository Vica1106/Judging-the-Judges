
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()
from langfuse.openai import openai
import os
import json
import argparse
import sys
import re

def LLM_Judge(major: str, word: str, system_prompt: str):
    #Create a chat completion using Langfuse-integrated OpenAI client
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

def load_prompt_file(prompt_file_path: str) -> str:
    """Load a prompt template from a JSON (with key 'prompt') or plain text file."""
    if not prompt_file_path:
        return "Explain the major term for me as short as possible."
    if not os.path.exists(prompt_file_path):
        print(f"Warning: Prompt file '{prompt_file_path}' not found. Falling back to default prompt.")
        return "Explain the major term for me as short as possible."
    try:
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            # Try JSON first
            try:
                data = json.loads(content)
                if isinstance(data, dict) and "prompt" in data and isinstance(data["prompt"], str):
                    return data["prompt"]
                # If JSON but no 'prompt' key, fall back to raw content
                return content
            except json.JSONDecodeError:
                # Not JSON; treat entire file as prompt text
                return content
    except Exception as e:
        print(f"Warning: Failed to read prompt file '{prompt_file_path}': {e}. Using default prompt.")
        return "Explain the major term for me as short as possible."

def build_output_path_with_prompt(output_path: str, prompt_file_path: str) -> str:
    """Append a sanitized prompt tag (from prompt filename) to the output filename."""
    directory, filename = os.path.split(output_path)
    name, ext = os.path.splitext(filename)
    prompt_base = os.path.splitext(os.path.basename(prompt_file_path))[0]
    prompt_tag = re.sub(r"[^A-Za-z0-9_\-]+", "-", prompt_base).strip("-_")
    new_filename = f"{name}__{prompt_tag}{ext}"
    return os.path.join(directory, new_filename) if directory else new_filename

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
    return f"{base_name}_top{top_n}.jsonl"

def process_jsonl_to_explanations(jsonl_path: str, output_path: str, top_n: int = 10, prompt_template: str = ""):
    """Read JSONL results, find top N by average score, and generate explanations"""
    top_k_filename = generate_top_k_filename(jsonl_path, top_n)
    top_entries = []
    
    # Check if top k file already exists
    print(f"Looking for existing top {top_n} file at: {top_k_filename}")
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
        print(f"Top k file not found at: {top_k_filename}")
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
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in top_entries:
            term = entry.get("Term", "")
            # Format the system prompt per term, replacing {concept} if present
            formatted_system_prompt = (prompt_template or "Explain the major term for me as short as possible.").replace("{concept}", term)
            result = LLM_Judge(major, term, formatted_system_prompt)
            
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
    parser.add_argument("--input", type=str, default="data/judged_dataset/glossary_of_AI_results_top10.jsonl", help="Path to input JSONL file from data_filter.py")
    parser.add_argument("--output", type=str, default="data/response_dataset/top_explanations_AI.jsonl", help="Path to output JSONL file (default: top_explanations.jsonl)")
    parser.add_argument("--top", type=int, default=10, help="Number of top terms to process (default: 10)")
    parser.add_argument("--prompt-file", type=str, default="prompts/baseline.json", help="Path to prompt file (JSON with 'prompt' key or plain text).")
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found.")
        sys.exit(1)
    
    prompt_template = load_prompt_file(args.prompt_file)
    output_with_tag = build_output_path_with_prompt(args.output, args.prompt_file)
    process_jsonl_to_explanations(args.input, output_with_tag, args.top, prompt_template)
   