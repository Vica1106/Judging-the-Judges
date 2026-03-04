import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent

# Mapping from old variant names to new ones
NAME_MAP = {
    "5step_round2": "5steps_round2",
    "academic": "Highly_formal_academic",
    "academic_round2": "Highly_formal_academic_round2",
}


def rename_in_evaluation_results():
    """
    Update prompt names in result/evaluation_results.jsonl and normalise comparison keys.

    - Renames old prompt labels using NAME_MAP in Prompt_A / Prompt_B.
    - Rebuilds Comparison as \"{Prompt_A} vs {Prompt_B}\" so it is clean and consistent.
    - Deduplicates multiple entries for the same (term, {prompt_a,prompt_b}) pair, keeping
      only the first occurrence.
    """
    path = ROOT / "result" / "evaluation_results.jsonl"
    if not path.exists():
        return

    tmp_path = path.with_suffix(".jsonl.tmp")

    seen = set()  # (term, tuple(sorted([prompt_a, prompt_b])))

    with path.open("r", encoding="utf-8") as fin, tmp_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            obj = json.loads(line)

            # Rename Prompt_A / Prompt_B
            for key in ("Prompt_A", "Prompt_B"):
                val = obj.get(key)
                if val in NAME_MAP:
                    obj[key] = NAME_MAP[val]

            prompt_a = obj.get("Prompt_A")
            prompt_b = obj.get("Prompt_B")
            term = obj.get("Term", "")

            # If we don't have both prompts or term, just write it through
            if not term or not prompt_a or not prompt_b:
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                continue

            # Build canonical key for deduplication
            canonical = (term, tuple(sorted([prompt_a, prompt_b])))
            if canonical in seen:
                # Skip duplicate comparison (already have a result for this pair & term)
                continue
            seen.add(canonical)

            # Normalise Comparison string to match Prompt_A / Prompt_B exactly
            obj["Comparison"] = f"{prompt_a} vs {prompt_b}"

            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")

    path.unlink()
    tmp_path.rename(path)


def rename_in_human_eval():
    """Update prompt names in result/human_eval_rankings.json."""
    path = ROOT / "result" / "human_eval_rankings.json"
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    averages = data.get("averages", {})
    # Rename keys in averages
    for old, new in list(NAME_MAP.items()):
        if old in averages and new not in averages:
            averages[new] = averages.pop(old)

    # Rename in ranking list
    for item in data.get("ranking", []):
        prompt = item.get("prompt")
        if prompt in NAME_MAP:
            item["prompt"] = NAME_MAP[prompt]

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def rename_in_elo_ratings():
    """Update prompt names in result/elo_ratings.json."""
    path = ROOT / "result" / "elo_ratings.json"
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    elo = data.get("elo_ratings", {})
    # Rename keys in elo_ratings
    for old, new in list(NAME_MAP.items()):
        if old in elo and new not in elo:
            elo[new] = elo.pop(old)

    # Rename in ranking list
    for item in data.get("ranking", []):
        key = "Prompt" if "Prompt" in item else "prompt"
        val = item.get(key)
        if val in NAME_MAP:
            item[key] = NAME_MAP[val]

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    rename_in_evaluation_results()
    rename_in_human_eval()
    rename_in_elo_ratings()


if __name__ == "__main__":
    main()

