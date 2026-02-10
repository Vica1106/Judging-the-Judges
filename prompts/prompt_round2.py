import json
import argparse
import json
from collections import defaultdict
import os
from typing import List, Dict
from langfuse.openai import openai

prompt_families = ['baseline', 'level2_multi_aspect', '5_step', 'casual', 'Highly_formal_academic']

def load_eval(path):
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def load_prompt_text(file_path):
    with open(file_path, "r", encoding='utf-8') as f:
        obj = json.load(f)
    if "prompt" not in obj:
        raise ValueError(f"Prompt file missing 'prompt' key: {file_path}")
    return obj['prompt']

def _add_feedback(bucket: Dict[str, List[str]], loser_prompt: str, term: str, major: str, opponent_prompt: str, reasoning: str, weaknesses: str, direction: str,):
    block = (
        f"Term: {term} | Major: {major}\n"
        f"Compared vs: {opponent_prompt} ({direction})\n"
        f"Judge reasoning: {reasoning}\n"
        f"Weaknesses: {weaknesses}\n"
    )
    bucket[loser_prompt].append(block)

def aggregate_feedback(eval_rows: List[dict], max_losses_per_prompt: int):
    '''Aggregate feedback per prompt family from both judgment_ab and judgment_ba'''
    feedback = defaultdict(list)
    def can_add(p):
        return (max_losses_per_prompt <= 0) or (len(feedback[p]) < max_losses_per_prompt)
    for r in eval_rows:
        term = r.get("Term", "")
        major = r.get("Major", "")
        prompt_a = r.get("Prompt_A")
        prompt_b = r.get("Prompt_B")

        jab = r.get("Judgment_AB", {}) or {}
        win_ab = jab.get("winner", "")
        reasoning_ab = jab.get("reasoning", "")
        weak_a = jab.get("weakness_A", "")
        weak_b = jab.get("weakness_B", "")

        if win_ab == "A":
            if prompt_b in prompt_families and can_add(prompt_b):
                _add_feedback(
                    feedback, prompt_b, term, major, prompt_a, reasoning_ab, weak_b, direction="AB (A wins)"
                )
        elif win_ab == "B":
            if prompt_a in prompt_families and can_add(prompt_a):
                _add_feedback(
                    feedback, prompt_a, term, major, prompt_b, reasoning_ab, weak_a, direction="AB (B wins)"
                )

        jba = r.get("Judgment_BA", {}) or {}
        win_ba = jba.get("winner", "")
        reasoning_ba = jba.get("reasoning", "")
        weak_a_ba = jba.get("weaknesses_A", "")
        weak_b_ba = jba.get("weaknesses_B", "")

        if win_ba == "A":
            if prompt_a in prompt_families and can_add(prompt_a):
                _add_feedback(
                    feedback, prompt_a, term, major, prompt_b, reasoning_ba, weak_b_ba, direction="BA (A wins)"
                )
        elif win_ba == "B":
            if prompt_b in prompt_families and can_add(prompt_b):
                _add_feedback(
                    feedback, prompt_b, term, major, prompt_a, reasoning_ba, weak_a_ba, direction="BA (B wins)"
                )
    return feedback

def build_meta_prompt(original_prompt: str, feedback_blocks: List[str]):
    feedback_text = "\n---\n".join(feedback_blocks)
    return f"""
You are optimizing an *explanation-generation prompt* used to produce more human understandable and readable explanations.
This is NOT an evaluation/judge prompt.

You will be given:
1) The ORIGINAL prompt template (uses placeholder {{concept}})
2) Aggregated judge feedback describing common failure patterns

Your task:
Rewrite the ORIGINAL prompt template so that future explanations better address these failures and support better undderstanding for college students (outside this major).

STEP 1: identify the 2-3 most frequent failure patterns implied by the feedback. 
STEP 2: rewrite the original prompt template by refining or modifying instructions that directly counter these failure patterns, aiming to help college students have a clear, helpful and easy to follow understandings in the concept.

Hard requirements:
- Keep the same placeholder name: {{concept}}
- Keep explanation length <= 200 words (explicitly instruct this)
- Do NOT request user interaction or follow-up questions
- Do NOT output chain-of-thought

Do NOT merely rewrite generic writing advice. Make modifications clearly motivated by the feedback patterns.
Return ONLY the revised prompt template text.

=== ORIGINAL PROMPT TEMPLATE ===
{original_prompt}

=== AGGREGATED ROUND 1 FEEDBACK (loss cases) ===
{feedback_text}
""".strip()

def call_llm_optimize(model, meta_prompt):
    resp = openai.chat.completions.create(
        model = model,
        messages = [
            {"role": "system", "content": "You are a highly experienced prompt optimization expert. Output only the revised prompt text."},
            {"role": "user", "content": meta_prompt},
        ],
    )
    return resp.choices[0].message.content.strip()

def write_prompt_json(path: str, prompt_text: str, description: str, base_prompt_path: str, model: str, losses_used: int):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    obj = {
        "prompt": prompt_text,
        "description": description,
        "base_prompt": base_prompt_path,
        "meta_model": model,
        "loss_examples_used": losses_used,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval_path", default="result/evaluation_results.jsonl")
    ap.add_argument("--prompt_dir", default="prompts")
    ap.add_argument("--out_dir", default="prompts/round2")
    ap.add_argument("--model", default="gpt-5-nano-2025-08-07")
    ap.add_argument("--max_losses_per_prompt", type=int, default=0,
                    help="Cap loss-case feedback blocks per prompt family. 0 = no cap.")
    args = ap.parse_args()

    eval_rows = load_eval(args.eval_path)
    feedback = aggregate_feedback(eval_rows, args.max_losses_per_prompt)
    prompt_paths = {
        "baseline": os.path.join(args.prompt_dir, "baseline.json"),
        "level2_multi_aspect": os.path.join(args.prompt_dir, "level2_multi_aspect.json"),
        "5_step": os.path.join(args.prompt_dir, "5_step.json"),
        "casual": os.path.join(args.prompt_dir, "casual.json"),
        "Highly_formal_academic": os.path.join(args.prompt_dir, "Highly_formal_academic.json"),
    }
    out_paths = {
        "baseline": os.path.join(args.out_dir, "baseline_round2.json"),
        "level2_multi_aspect": os.path.join(args.out_dir, "level2_multi_aspect_round2.json"),
        "5_step": os.path.join(args.out_dir, "5step_round2.json"),
        "casual": os.path.join(args.out_dir, "casual_round2.json"),
        "Highly_formal_academic": os.path.join(args.out_dir, "Highly_formal_academic_round2.json"),
    }

    for p in prompt_families:
        base_path = prompt_paths[p]
        out_path = out_paths[p]
        original_prompt = load_prompt_text(base_path)
        blocks = feedback.get(p, [])
        if not blocks:
            blocks = ["No loss feedback found; imrpove clarity and structure for college students' understanding"]
        meta_prompt = build_meta_prompt(original_prompt, blocks)
        optimized_text = call_llm_optimize(args.model, meta_prompt)
    
        desc = f"Round2 optimized generation prompt for {p}, derived from Round1 evaluation feedback."
        write_prompt_json(
            out_path,
            optimized_text,
            desc,
            base_path,
            args.model,
            losses_used=len(blocks) if blocks else 0,
        )

        print(f"✅ Wrote: {out_path}  (loss blocks used: {len(blocks)})")


if __name__ == "__main__":
    main()
