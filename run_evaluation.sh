#!/bin/bash

# Script to run pairwise evaluation and analysis
# Usage: ./run_evaluation.sh [evaluation_output] [elo_output]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default output files
EVALUATION_OUTPUT="${1:-result/evaluation_results.jsonl}"
ELO_OUTPUT="${2:-result/elo_ratings.json}"

echo "=========================================="
echo "Step 1: Running pairwise evaluation..."
echo "=========================================="
echo ""

# Run the evaluation (script will automatically find all JSONL files)
python "$SCRIPT_DIR/evaluate_explanations.py" --output "$EVALUATION_OUTPUT"

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Evaluation failed."
    exit 1
fi

echo ""
echo "=========================================="
echo "Step 2: Analyzing results and calculating Elo ratings..."
echo "=========================================="
echo ""

# Run the analysis
python "$SCRIPT_DIR/analyze_evaluation.py" --input "$EVALUATION_OUTPUT" --output "$ELO_OUTPUT"

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Complete pipeline finished successfully!"
    echo "=========================================="
    echo ""
    echo "Results saved to:"
    echo "  - Evaluation results: $EVALUATION_OUTPUT"
    echo "  - Elo ratings: $ELO_OUTPUT"
else
    echo ""
    echo "❌ Analysis failed."
    exit 1
fi

