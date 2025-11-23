import json
import os
import argparse
from collections import defaultdict

def calculate_elo_ratings(results, initial_rating=1500, k_factor=32):
    """
    Calculate Elo ratings from pairwise comparison results.
    
    Args:
        results: List of comparison result dictionaries
        initial_rating: Starting Elo rating (default 1500)
        k_factor: K-factor for rating updates (default 32)
    
    Returns:
        Dictionary mapping prompt names to Elo ratings
    """
    # Initialize ratings for all prompts
    elo_ratings = defaultdict(lambda: initial_rating)
    
    # Process results in order to update ratings
    for result in results:
        prompt_a = result.get("Prompt_A", "")
        prompt_b = result.get("Prompt_B", "")
        winner = result.get("Winner", "").lower()
        
        if not prompt_a or not prompt_b or winner == "error":
            continue
        
        # Get current ratings
        rating_a = elo_ratings[prompt_a]
        rating_b = elo_ratings[prompt_b]
        
        # Calculate expected scores
        expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
        expected_b = 1 / (1 + 10 ** ((rating_a - rating_b) / 400))
        
        # Determine actual scores based on winner
        if winner == "a":
            actual_a = 1.0
            actual_b = 0.0
        elif winner == "b":
            actual_a = 0.0
            actual_b = 1.0
        elif winner == "tie":
            actual_a = 0.5
            actual_b = 0.5
        else:
            continue  # Skip unknown results
        
        # Update ratings
        elo_ratings[prompt_a] = rating_a + k_factor * (actual_a - expected_a)
        elo_ratings[prompt_b] = rating_b + k_factor * (actual_b - expected_b)
    
    return dict(elo_ratings)

def analyze_evaluation_results(input_path: str, initial_rating=1500, k_factor=32):
    """Analyze evaluation results and print summary statistics"""
    if not os.path.exists(input_path):
        print(f"Error: File '{input_path}' not found.")
        return None
    
    results = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line.strip()))
    
    if not results:
        print("No results found in file.")
        return None
    
    print(f"Analysis of Evaluation Results")
    print("=" * 60)
    print(f"Total comparisons: {len(results)}")
    print("")
    
    # Statistics by comparison type
    comparison_stats = defaultdict(lambda: {"a": 0, "b": 0, "tie": 0, "error": 0})
    prompt_wins = defaultdict(int)
    prompt_losses = defaultdict(int)
    prompt_ties = defaultdict(int)
    
    for result in results:
        comparison = result.get("Comparison", "")
        winner = result.get("Winner", "").lower()
        prompt_a = result.get("Prompt_A", "")
        prompt_b = result.get("Prompt_B", "")
        
        # Normalize winner to lowercase for consistent key access
        winner_normalized = winner if winner in ["a", "b", "tie", "error"] else "error"
        comparison_stats[comparison][winner_normalized] = comparison_stats[comparison][winner_normalized] + 1
        
        if winner == "a":
            prompt_wins[prompt_a] += 1
            prompt_losses[prompt_b] += 1
        elif winner == "b":
            prompt_wins[prompt_b] += 1
            prompt_losses[prompt_a] += 1
        elif winner == "tie":
            prompt_ties[prompt_a] += 1
            prompt_ties[prompt_b] += 1
    
    # Print comparison-by-comparison statistics
    print("Results by Comparison Type:")
    print("-" * 60)
    for comparison, stats in sorted(comparison_stats.items()):
        total = sum(stats.values())
        print(f"\n{comparison}:")
        print(f"  Total: {total}")
        if total > 0:
            print(f"  A wins: {stats.get('a', 0)} ({stats.get('a', 0)/total*100:.1f}%)")
            print(f"  B wins: {stats.get('b', 0)} ({stats.get('b', 0)/total*100:.1f}%)")
            print(f"  Ties: {stats.get('tie', 0)} ({stats.get('tie', 0)/total*100:.1f}%)")
        else:
            print(f"  A wins: 0 (0.0%)")
            print(f"  B wins: 0 (0.0%)")
            print(f"  Ties: 0 (0.0%)")
        if stats.get('error', 0) > 0:
            print(f"  Errors: {stats.get('error', 0)}")
    
    # Print overall prompt performance
    print("\n" + "=" * 60)
    print("Overall Prompt Performance:")
    print("-" * 60)
    all_prompts = set(prompt_wins.keys()) | set(prompt_losses.keys()) | set(prompt_ties.keys())
    
    for prompt in sorted(all_prompts):
        wins = prompt_wins.get(prompt, 0)
        losses = prompt_losses.get(prompt, 0)
        ties = prompt_ties.get(prompt, 0)
        total = wins + losses + ties
        win_rate = (wins / total * 100) if total > 0 else 0
        
        print(f"\n{prompt}:")
        print(f"  Wins: {wins}")
        print(f"  Losses: {losses}")
        print(f"  Ties: {ties}")
        print(f"  Total: {total}")
        print(f"  Win Rate: {win_rate:.1f}%")
    
    # Terms with most disagreements
    print("\n" + "=" * 60)
    print("Terms with Most Disagreements (not all ties):")
    print("-" * 60)
    term_stats = defaultdict(lambda: {"ties": 0, "non_ties": 0})
    
    for result in results:
        term = result.get("Term", "")
        winner = result.get("Winner", "").lower()
        if winner == "tie":
            term_stats[term]["ties"] += 1
        else:
            term_stats[term]["non_ties"] += 1
    
    # Sort by non-ties (most disagreements first)
    sorted_terms = sorted(term_stats.items(), key=lambda x: x[1]["non_ties"], reverse=True)
    
    print("\nTop 10 terms with most non-tie results:")
    for term, stats in sorted_terms[:10]:
        total = stats["ties"] + stats["non_ties"]
        print(f"  {term}: {stats['non_ties']} non-ties, {stats['ties']} ties (out of {total} comparisons)")
    
    # Calculate Elo ratings
    print("\n" + "=" * 60)
    print("Calculating Elo Ratings...")
    print("-" * 60)
    elo_ratings = calculate_elo_ratings(results, initial_rating, k_factor)
    
    # Create ranking sorted by Elo (descending)
    ranking = []
    for rank, (prompt, elo) in enumerate(sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True), 1):
        ranking.append({
            "rank": rank,
            "Prompt": prompt,
            "elo": round(elo, 2)
        })
        print(f"  Rank {rank}: {prompt} - Elo: {elo:.2f}")
    
    return {
        "elo_ratings": {prompt: round(elo, 2) for prompt, elo in elo_ratings.items()},
        "ranking": ranking
    }

def save_elo_results(elo_data, output_path: str):
    """Save Elo ratings and ranking to JSON file"""
    # Round Elo ratings for cleaner output
    rounded_ratings = {prompt: round(elo, 2) for prompt, elo in elo_data["elo_ratings"].items()}
    
    output = {
        "elo_ratings": rounded_ratings,
        "ranking": elo_data["ranking"]
    }
    
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Elo ratings saved to: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze evaluation results and calculate Elo ratings")
    parser.add_argument("--input", type=str, default="result/evaluation_results.jsonl",
                       help="Path to evaluation results JSONL file")
    parser.add_argument("--output", type=str, default="result/elo_ratings.json",
                       help="Path to output JSON file with Elo ratings and ranking")
    parser.add_argument("--k-factor", type=float, default=32.0,
                       help="K-factor for Elo rating updates (default: 32)")
    parser.add_argument("--initial-rating", type=float, default=1500.0,
                       help="Initial Elo rating (default: 1500)")
    
    args = parser.parse_args()
    
    # Run analysis and get Elo ratings
    elo_data = analyze_evaluation_results(args.input, args.initial_rating, args.k_factor)
    
    if elo_data:
        save_elo_results(elo_data, args.output)
    else:
        print(f"Error: Could not process results from {args.input}")

