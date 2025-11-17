#!/bin/bash

# Script to process all CSV files in the data folder using data_filter.py
# Usage: ./process_all_csv.sh [--output OUTPUT_FILE]
# If --output is not specified, each CSV will have its own output file

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/data/raw_data"
PYTHON_SCRIPT="$SCRIPT_DIR/data/data_filter.py"

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

# Parse command line arguments
OUTPUT_FILE=""
if [ "$1" == "--output" ] && [ -n "$2" ]; then
    OUTPUT_FILE="$2"
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
    
    # Determine output file
    if [ -n "$OUTPUT_FILE" ]; then
        output_path="$SCRIPT_DIR/$OUTPUT_FILE"
    else
        # Create output filename based on input filename
        output_filename=$(basename "$csv_file" .csv)_results.jsonl
        output_path="$SCRIPT_DIR/data/judged_dataset/$output_filename"
    fi
    
    echo "Processing: $filename"
    echo "  Major: $major"
    echo "  Output: $output_path"
    echo ""
    
    # Run the Python script
    python "$PYTHON_SCRIPT" --major "$major" --input "$csv_file" --output "$output_path"
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully processed $filename"
    else
        echo "❌ Error processing $filename"
    fi
    echo ""
done

echo "All CSV files processed!"

