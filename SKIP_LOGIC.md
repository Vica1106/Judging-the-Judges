# Skip Logic Documentation

This document describes how each script handles existing output files to avoid duplicate processing.

**Note**: All log files are saved to `utils/logger/` directory with timestamps.

## Overview

All scripts are designed to skip processing if the output file already exists and contains the corresponding data. This prevents:
- Duplicate API calls (saving costs)
- Unnecessary processing time
- Data duplication

## Script-by-Script Details

### 1. `data/data_filter.py`

**Output file**: JSONL file with judged concept difficulty scores

**Skip logic**:
- Reads existing output file and extracts all processed `Term` values
- Skips terms that already exist in the output file
- Uses **append mode** (`"a"`) to add only new entries
- Reports: `{processed_count} new entries processed, {skipped_count} skipped`

**Example**:
```python
# If output file contains:
{"Term": "algorithm", "Complexity": 5, ...}
{"Term": "data structure", "Complexity": 6, ...}

# And CSV contains: algorithm, data structure, recursion
# Result: Only "recursion" will be processed
```

### 2. `data/response_generator.py`

**Output files**: 
- Top-k file: `{input}_top{k}.jsonl` (intermediate file)
- Final output: Explanation JSONL file

**Skip logic**:
1. **Top-k file check**: If `{input}_top{k}.jsonl` exists and is not empty, uses it instead of re-selecting top-k terms
2. **Output file check**: Reads existing output file and extracts all processed `Term` values
   - Skips terms that already exist in the output file
   - Uses **append mode** (`"a"`) to add only new entries
3. Reports: `{processed_count} new entries processed, {skipped_count} skipped`

**Example**:
```python
# If top_k file exists: Uses it directly
# If output file contains:
{"Term": "algorithm", "Explanation": "..."}
{"Term": "data structure", "Explanation": "..."}

# And top_k contains: algorithm, data structure, recursion
# Result: Only "recursion" will be processed
```

### 3. `analyze/evaluate_explanations.py`

**Output file**: JSONL file with pairwise comparison results

**Skip logic**:
- Loads all existing results from output file
- For each (term, comparison) pair, checks if it already exists
- Skips already processed comparisons
- Uses **write mode** (`"w"`) to save complete results (existing + new)
- Preserves all existing results while adding new ones
- Reports: `New comparisons: {count}, Skipped: {count}, Total comparisons: {count}`

**Example**:
```python
# If output file contains:
{"Term": "algorithm", "Comparison": "baseline vs level2", ...}
{"Term": "algorithm", "Comparison": "baseline vs casual", ...}

# And needs to compare: algorithm (baseline vs level2, baseline vs casual, level2 vs casual)
# Result: Only "level2 vs casual" will be processed
```

### 4. `analyze/analyze_evaluation.py`

**Output file**: JSON file with Elo ratings and ranking

**Skip logic**:
- Checks if output file exists
- Compares modification times: if output is newer than input, skips recalculation
- If input file has changed, recalculates Elo ratings
- Reports: `Output file already exists and is up to date. Skipping recalculation.`

**Example**:
```python
# If output file exists and input file hasn't changed:
# Result: Skips entire calculation, reports "skipped"

# If input file is newer than output:
# Result: Recalculates and overwrites output
```

## Key Features

1. **Incremental Processing**: All scripts support resuming from where they left off
2. **No Data Loss**: Existing data is always preserved
3. **Efficient**: Only processes new/missing data
4. **Safe Re-runs**: You can safely re-run any script without losing progress

## File Modes

- **Append mode (`"a"`)**: Used by `data_filter.py` and `response_generator.py`
  - Adds new entries to existing file
  - Preserves all existing data
  
- **Write mode (`"w"`)**: Used by `evaluate_explanations.py` and `analyze_evaluation.py`
  - Overwrites file with complete results (existing + new)
  - Ensures data consistency

## Best Practices

1. **Don't delete output files** unless you want to reprocess everything
2. **Check logs** in `utils/logger/` folder to see what was skipped
3. **Re-run scripts** anytime - they'll automatically skip processed items
4. **Monitor skipped counts** to verify skip logic is working
