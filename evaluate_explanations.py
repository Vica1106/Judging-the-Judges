from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()
from langfuse.openai import openai
import os
import json
import argparse
import sys
from itertools import combinations

def load_jsonl(file_path: str):
    """Load entries from a JSONL file"""
    entries = {}
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return entries
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entry = json.loads(line.strip())
                term = entry.get("Term", "")
                if term:
                    entries[term] = entry
    return entries

def pairwise_judge(major: str, term: str, explanation_a: str, explanation_b: str, prompt_name_a: str, prompt_name_b: str):
    """Use LLM to judge which explanation is better"""
    system_prompt = """You are a highly experienced educator who understands how real college students read and learn. Your role is to judge which of two explanations would be preferred by a typical non-expert college student.

Your evaluation must be human-centered. Imagine a real student reading these explanations between classes, with limited patience and no background in the major.

Focus on:
- How easy the explanation feels to read on the first pass.
- Whether it gives a clear, intuitive "now I get it" feeling.
- How approachable and non-intimidating the wording is.
- Whether it avoids unnecessary jargon or complexity.
- Whether the explanation is the right length — not too long or overwhelming.  
  (Humans lose patience quickly; long, dense explanations reduce understanding.)
- Overall, which explanation a real student would *actually prefer* because it is easier to follow and more helpful.

You are not grading research papers. You are judging which explanation best supports real human understanding.

Choose the explanation that a typical college student (outside this major) would genuinely find more readable, more helpful, and more pleasant to learn from.

Return your decision in JSON format.
    """
    
    user_prompt = f"""
    Major: {major}
Term: {term}

Explanation A (from {prompt_name_a}):
{explanation_a}

Explanation B (from {prompt_name_b}):
{explanation_b}

Which explanation would a typical non-expert college student find easier to understand, more readable, and more helpful—considering clarity, approachability, and human patience for long or dense explanations?

Please respond in the following JSON format:

{{
    "winner": "A" or "B" or "tie",
    "reasoning": "A short explanation describing why a student would prefer this explanation",
    "strengths_A": "What parts of A appeal to or help a student",
    "strengths_B": "What parts of B appeal to or help a student",
    "weaknesses_A": "What parts of A might confuse, overwhelm, or feel too long",
    "weaknesses_B": "What parts of B might confuse, overwhelm, or feel too long"
}}

    """
    
    completion = openai.chat.completions.create(
        name="evaluation-judge",
        model="gpt-5-nano-2025-08-07",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        metadata={"task": "pairwise_evaluation"}
    )
    
    result_text = completion.choices[0].message.content
    
    # Try to parse JSON from the response
    try:
        # Extract JSON if it's wrapped in markdown code blocks
        if "```json" in result_text:
            json_start = result_text.find("```json") + 7
            json_end = result_text.find("```", json_start)
            result_text = result_text[json_start:json_end].strip()
        elif "```" in result_text:
            json_start = result_text.find("```") + 3
            json_end = result_text.find("```", json_start)
            result_text = result_text[json_start:json_end].strip()
        
        result = json.loads(result_text)
        return result
    except json.JSONDecodeError:
        # If JSON parsing fails, return a structured response
        return {
            "winner": "error",
            "reasoning": f"Failed to parse JSON. Raw response: {result_text[:200]}",
            "raw_response": result_text
        }

def pairwise_judge_with_retry(major: str, term: str, explanation_a: str, explanation_b: str, prompt_name_a: str, prompt_name_b: str, max_retries=3):
    """
    Judge with retry logic. Retries up to max_retries times if result is "error".
    Returns immediately if result is "a", "b", or "tie".
    """
    for attempt in range(1, max_retries + 1):
        judgment = pairwise_judge(major, term, explanation_a, explanation_b, prompt_name_a, prompt_name_b)
        winner = judgment.get("winner", "error").lower()
        
        # If result is valid (a, b, or tie), return immediately
        if winner in ["a", "b", "tie"]:
            return judgment
        
        # If result is error and we have retries left, retry
        if attempt < max_retries:
            print(f"    ⚠️  Got error result, retrying ({attempt}/{max_retries})...")
        else:
            print(f"    ❌ Max retries ({max_retries}) reached, keeping error result")
    
    # Return the last error result if all retries exhausted
    return judgment

def extract_prompt_name(file_path: str):
    """Extract prompt name from filename (e.g., 'baseline' from 'top_explanations_AI__baseline.jsonl')"""
    filename = os.path.basename(file_path)
    if "__" in filename:
        parts = filename.split("__")
        if len(parts) > 1:
            prompt_part = parts[1].replace(".jsonl", "")
            return prompt_part
    return os.path.splitext(filename)[0]

def find_jsonl_files(directory: str):
    """Find all JSONL files in the specified directory"""
    jsonl_files = []
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' not found.")
        return jsonl_files
    
    for filename in os.listdir(directory):
        if filename.endswith('.jsonl'):
            file_path = os.path.join(directory, filename)
            jsonl_files.append(file_path)
    
    return sorted(jsonl_files)

def combine_judgments(judgment_ab, judgment_ba):
    """
    Combine two judgments from different orders (A,B) and (B,A).
    Logic: If both agree on a winner, use that winner. Otherwise, it's a tie.
    
    In judgment_ab: A = prompt_a, B = prompt_b
    In judgment_ba: A = prompt_b, B = prompt_a (order is swapped)
    
    So to compare:
    - If judgment_ab says "A" wins and judgment_ba says "B" wins → both say prompt_a wins → A wins
    - If judgment_ab says "B" wins and judgment_ba says "A" wins → both say prompt_b wins → B wins
    - Otherwise → tie
    """
    winner_ab = judgment_ab.get("winner", "").lower()
    winner_ba = judgment_ba.get("winner", "").lower()
    
    # Handle errors
    if winner_ab == "error" or winner_ba == "error":
        return "tie"
    
    # Determine what each judgment means in terms of prompt_a vs prompt_b
    # judgment_ab: "a" = prompt_a wins, "b" = prompt_b wins
    # judgment_ba: "a" = prompt_b wins (because A in BA is prompt_b), "b" = prompt_a wins (because B in BA is prompt_a)
    
    prompt_a_wins_ab = (winner_ab == "a")
    prompt_b_wins_ab = (winner_ab == "b")
    prompt_a_wins_ba = (winner_ba == "b")  # In BA order, B means prompt_a
    prompt_b_wins_ba = (winner_ba == "a")  # In BA order, A means prompt_b
    
    # Check if both agree on prompt_a winning
    if prompt_a_wins_ab and prompt_a_wins_ba:
        return "A"
    # Check if both agree on prompt_b winning
    elif prompt_b_wins_ab and prompt_b_wins_ba:
        return "B"
    # Otherwise, it's a tie (disagreement or any original tie)
    else:
        return "tie"

def get_processed_comparisons(output_path: str):
    """Read existing output file and return set of already processed (term, comparison) pairs"""
    processed = set()
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line.strip())
                        term = entry.get("Term", "")
                        comparison = entry.get("Comparison", "")
                        if term and comparison:
                            processed.add((term, comparison))
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read existing output file: {e}")
    return processed

def evaluate_explanations(file_paths: list, output_path: str):
    """Main evaluation function"""
    if len(file_paths) < 2:
        print("Error: Need at least 2 files to compare.")
        return
    
    # Load all files
    print("Loading explanation files...")
    all_entries = {}
    prompt_names = {}
    
    for file_path in file_paths:
        prompt_name = extract_prompt_name(file_path)
        prompt_names[file_path] = prompt_name
        entries = load_jsonl(file_path)
        all_entries[file_path] = entries
        print(f"  Loaded {len(entries)} entries from {prompt_name} ({os.path.basename(file_path)})")
    
    # Find common terms
    if not all_entries:
        print("Error: No entries loaded.")
        return
    
    # Get all terms from first file
    first_file = file_paths[0]
    common_terms = set(all_entries[first_file].keys())
    
    # Find intersection of all terms
    for file_path in file_paths[1:]:
        common_terms = common_terms.intersection(set(all_entries[file_path].keys()))
    
    print(f"\nFound {len(common_terms)} common terms across all files.")
    print("")
    
    if not common_terms:
        print("Error: No common terms found across files.")
        return
    
    # Generate all pairwise comparisons
    comparisons = list(combinations(file_paths, 2))
    # Each comparison will be judged twice (A,B and B,A), so total is still the same
    print(f"Will perform {len(comparisons)} pairwise comparisons per term (with order swapping: {len(comparisons) * len(common_terms)} total comparisons).")
    print("Each pair will be judged in both orders (A,B and B,A) and results will be combined.")
    print("")
    
    # Check for already processed comparisons
    processed = get_processed_comparisons(output_path)
    if processed:
        print(f"Found {len(processed)} already processed comparisons. Skipping those...")
        print("")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    # Load existing results if file exists
    existing_results = []
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    existing_results.append(json.loads(line.strip()))
    
    # Process each term
    results = existing_results.copy()
    total_comparisons = len(common_terms) * len(comparisons)
    skipped_count = 0
    processed_count = len(existing_results)
    current_comparison = processed_count
    
    for term in sorted(common_terms):
        # Get major from first entry (should be same across all)
        major = all_entries[first_file][term].get("Major", "")
        
        # Perform all pairwise comparisons for this term
        for file_a, file_b in comparisons:
            prompt_a = prompt_names[file_a]
            prompt_b = prompt_names[file_b]
            comparison_key = f"{prompt_a} vs {prompt_b}"
            
            # Check if already processed
            if (term, comparison_key) in processed:
                skipped_count += 1
                print(f"⏭️  Skipped (already processed): {term} - {comparison_key}")
                continue
            
            current_comparison += 1
            explanation_a = all_entries[file_a][term].get("Explanation", "")
            explanation_b = all_entries[file_b][term].get("Explanation", "")
            
            print(f"[{current_comparison}/{total_comparisons}] Comparing {prompt_a} vs {prompt_b} for term: {term}")
            print(f"  Step 1: Judging ({prompt_a}, {prompt_b}) order...")
            
            # Get judgment in A,B order with retry
            judgment_ab = pairwise_judge_with_retry(major, term, explanation_a, explanation_b, prompt_a, prompt_b)
            winner_ab = judgment_ab.get("winner", "unknown").lower()
            print(f"    Result: {winner_ab}")
            
            print(f"  Step 2: Judging ({prompt_b}, {prompt_a}) order (swapped)...")
            
            # Get judgment in B,A order (swapped) with retry
            judgment_ba = pairwise_judge_with_retry(major, term, explanation_b, explanation_a, prompt_b, prompt_a)
            winner_ba = judgment_ba.get("winner", "unknown").lower()
            print(f"    Result: {winner_ba}")
            
            # Combine judgments
            final_winner = combine_judgments(judgment_ab, judgment_ba)
            print(f"  Combined result: {final_winner}")
            print("")
            
            # Create result entry with both judgments
            result_entry = {
                "Term": term,
                "Major": major,
                "Comparison": comparison_key,
                "Prompt_A": prompt_a,
                "Prompt_B": prompt_b,
                "Explanation_A": explanation_a,
                "Explanation_B": explanation_b,
                "Winner": final_winner,
                "Judgment_AB": {
                    "winner": judgment_ab.get("winner", "unknown"),
                    "reasoning": judgment_ab.get("reasoning", ""),
                    "strengths_A": judgment_ab.get("strengths_A", ""),
                    "strengths_B": judgment_ab.get("strengths_B", ""),
                    "weaknesses_A": judgment_ab.get("weaknesses_A", ""),
                    "weaknesses_B": judgment_ab.get("weaknesses_B", "")
                },
                "Judgment_BA": {
                    "winner": judgment_ba.get("winner", "unknown"),
                    "reasoning": judgment_ba.get("reasoning", ""),
                    "strengths_A": judgment_ba.get("strengths_A", ""),  # Note: in BA order, A is actually B
                    "strengths_B": judgment_ba.get("strengths_B", ""),  # Note: in BA order, B is actually A
                    "weaknesses_A": judgment_ba.get("weaknesses_A", ""),
                    "weaknesses_B": judgment_ba.get("weaknesses_B", "")
                },
                "Reasoning": f"Combined from ({prompt_a},{prompt_b}): {judgment_ab.get('winner', 'unknown')}, ({prompt_b},{prompt_a}): {judgment_ba.get('winner', 'unknown')}"
            }
            
            results.append(result_entry)
            processed_count += 1
    
    # Save all results (overwrite with complete results)
    with open(output_path, "w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    
    print(f"✅ Evaluation complete! Results saved to: {output_path}")
    print(f"   New comparisons: {processed_count - len(existing_results)}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total comparisons: {len(results)}")
    
    # Print summary statistics
    print("\nSummary Statistics:")
    winner_counts = {}
    for result in results:
        winner = result["Winner"]
        comparison = result["Comparison"]
        key = f"{comparison}: {winner}"
        winner_counts[key] = winner_counts.get(key, 0) + 1
    
    for key, count in sorted(winner_counts.items()):
        print(f"  {key}: {count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate explanations from multiple prompt files using pairwise comparison")
    parser.add_argument("--files", type=str, nargs="+", default=None,
                       help="Paths to JSONL files containing explanations (optional, defaults to all JSONL files in response_dataset folder)")
    parser.add_argument("--response-dataset", type=str, default="data/response_dataset",
                       help="Directory containing JSONL files with explanations (default: data/response_dataset)")
    parser.add_argument("--output", type=str, default="result/evaluation_results.jsonl",
                       help="Path to output JSONL file with evaluation results")
    
    args = parser.parse_args()
    
    # If files not specified, find all JSONL files in response_dataset folder
    if args.files is None:
        print(f"Finding JSONL files in '{args.response_dataset}'...")
        file_paths = find_jsonl_files(args.response_dataset)
        
        if not file_paths:
            print(f"Error: No JSONL files found in '{args.response_dataset}'")
            sys.exit(1)
        
        print(f"Found {len(file_paths)} JSONL files:")
        for file_path in file_paths:
            print(f"  - {os.path.basename(file_path)}")
        print("")
    else:
        file_paths = args.files
    
    if len(file_paths) < 2:
        print("Error: Need at least 2 files to compare.")
        sys.exit(1)
    
    evaluate_explanations(file_paths, args.output)

