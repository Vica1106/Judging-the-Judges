#!/bin/bash

# Script to process all CSV files in the data folder using data_filter.py
# Usage: ./process_all_csv.sh [--output OUTPUT_FILE]
# If --output is not specified, each CSV will have its own output file

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/data/raw_data"
PYTHON_SCRIPT="$SCRIPT_DIR/data/data_filter.py"
RESPONSE_SCRIPT="$SCRIPT_DIR/data/response_generator.py"

# Prompt variants to generate responses for
PROMPT_VARIANTS=("baseline" "level2_multi_aspect" "level3_multi_perspective")
PROMPT_DIR="$SCRIPT_DIR/prompts"

# Check if data directory exists
if [ ! -d "$DATA_DIR" ]; then
    echo "Error: Data directory '$DATA_DIR' not found."
    exit 1
fi

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script '$PYTHON_SCRIPT' not found."
    exit 1
fi



# Function to extract major name from filename
# e.g., "glossary_of_AI.csv" -> "AI"
# e.g., "glossary_of_cs.csv" -> "Computer Science"
extract_major() {
    local filename=$(basename "$1" .csv)
    # Remove "glossary_of_" prefix
    local major=$(echo "$filename" | sed 's/glossary_of_//')
    
    # Convert abbreviations to full names
    case "$major" in
        "AI")
            echo "Artificial Intelligence"
            ;;
        "cs")
            echo "Computer Science"
            ;;
        "stats")
            echo "Statistics"
            ;;
        *)
            # Capitalize first letter of each word
            echo "$major" | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2));}1'
            ;;
    esac
}

# Function to extract major slug (directory name) from filename
# e.g., "glossary_of_AI.csv" -> "AI"
#       "glossary_of_cs.csv" -> "cs"
#       "glossary_of_stats.csv" -> "stats"
extract_major_slug() {
    local filename=$(basename "$1" .csv)
    echo "$filename" | sed 's/glossary_of_//'
}

# Process each CSV file in the data directory
echo "Starting to process CSV files in $DATA_DIR..."
echo ""

for csv_file in "$DATA_DIR"/*.csv; do
    # Check if any CSV files exist
    if [ ! -f "$csv_file" ]; then
        echo "No CSV files found in $DATA_DIR"
        exit 1
    fi
    
    filename=$(basename "$csv_file")
    major=$(extract_major "$filename")
    major_slug=$(extract_major_slug "$filename")
    
    # Judged dataset output path
    judged_dir="$SCRIPT_DIR/data/judged_dataset"
    mkdir -p "$judged_dir"
    judged_output_filename="$(basename "$csv_file" .csv)_results.jsonl"
    judged_output_path="$judged_dir/$judged_output_filename"
    
    echo "Processing: $filename"
    echo "  Major: $major"
    echo "  Judged output: $judged_output_path"
    echo ""
    
    # Run the judging step (scores only)
    python3 "$PYTHON_SCRIPT" --major "$major" --input "$csv_file" --output "$judged_output_path"
    
    if [ $? -ne 0 ]; then
        echo "❌ Error processing $filename"
        echo ""
        continue
    fi
    echo "✅ Judged: $filename"
    echo ""

    # Response generation step for each prompt variant
    for variant in "${PROMPT_VARIANTS[@]}"; do
        prompt_file="$PROMPT_DIR/$variant.json"
        response_dir="$SCRIPT_DIR/data/response_dataset/$variant"
        mkdir -p "$response_dir"
        response_output_filename="$(basename "$csv_file" .csv)_explanations.jsonl"
        response_output_path="$response_dir/$response_output_filename"

        echo "Generating responses ($variant):"
        echo "  Input (judged): $judged_output_path"
        echo "  Prompt: $prompt_file"
        echo "  Output (responses): $response_output_path"
        echo ""

        # Provide the original CSV so response generator can infer terms/major if missing
        # Use --no-tag so the filename is not suffixed with the prompt tag; variant is represented by folder
        python3 "$RESPONSE_SCRIPT" --input "$judged_output_path" --output "$response_output_path" --csv "$csv_file" --prompt-file "$prompt_file" --no-tag

        if [ $? -eq 0 ]; then
            echo "✅ Responses generated for $filename ($variant)"
        else
            echo "❌ Error generating responses for $filename ($variant)"
        fi
        echo ""
    done
done

echo "All CSV files processed!"

