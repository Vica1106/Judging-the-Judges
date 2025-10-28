
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()
from langfuse.openai import openai
import os
import pandas as pd
import json

def LLM_Judge(major: str, term: str, explanation: str = None):
    #Create a chat completion using Langfuse-integrated OpenAI client
    system_prompt = """
    You are an expert in interdisciplinary education and language complexity analysis. 
    Your task is to evaluate how difficult a given term from a specific academic major would be 
    for an average college student who is **not majoring in that field**, but who has taken some general education courses.

    For each input, you will receive:
    - **Major**: the academic field where the term belongs
    - **Term**: the word or phrase to be judged
    - **Explanation**: a short definition or contextual description (if provided)

    Please evaluate the term on the following dimensions, each rated from **1 to 10**, and return an number for each:

    1. **Specialization** - How exclusive is this term to the given major?  
    (1 = very common in everyday life, 10 = almost never seen outside this academic field)

    2. **Complexity** - How difficult is the concept to understand for someone without specialized training?  
    (1 = easily understood, 10 = requires advanced theoretical background or multiple sub-concepts)

    3. **Familiarity** - How likely is it that an average college student has heard this term before?  
    (1 = very likely, 10 = almost unknown to the general student population)

    4. **Explainability** - How easily can this concept be explained in one short, non-technical sentence?  
    (1 = very easy to explain simply, 10 = very hard to simplify without losing accuracy)

    5. **Interdisciplinary Reach** - How widely is this term used across multiple disciplines?  
    (1 = commonly used in several fields, 10 = only relevant in a single specialized subfield)

    6. **Cognitive Load** - How much abstract reasoning or technical background is required to understand the concept?  
    (1 = concrete and intuitive, 10 = highly abstract or mathematically demanding)

    Finally, provide a **short overall comment** summarizing whether this term would likely be difficult 
    for a non-major student to grasp quickly, based on your ratings.

    ### Output format (JSON preferred):
    {
    "Major": "...",
    "Term": "...",
    "Specialization": ,
    "Complexity": ,
    "Familiarity": ,
    "Explainability": ,
    "Interdisciplinary_Reach": ,
    "Cognitive_Load":,
    "Overall Assessment": "..."
    }
    """
    completion = openai.chat.completions.create(
        name="judge-chat",
        model="gpt-5-nano-2025-08-07",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": major + "\n\nTerm: " + term + (f"\n\nExplanation: {explanation}" if explanation else "")}
        ],
        metadata={"task": "judging"}
    )
    # print(completion)
    return completion.choices[0].message.content

def process_csv_to_jsonl(major:str, csv_path: str, output_path: str):
    df = pd.read_csv(csv_path)
    
    with open(output_path, "a", encoding="utf-8") as f:
        # for _, row in df.iterrows():
        for _, row in df.head().iterrows():
            term = row.get("term", "")
            explanation = row.get("definition", None)
            
            result = LLM_Judge(major, term, explanation)
            f.write(json.dumps(json.loads(result), ensure_ascii=False) + "\n")
            print(f"✅ Processed: {term}")

if __name__ == "__main__":
    input_csv = "data/glossary_of_physics.csv"
    output_jsonl = "results.jsonl"
    major = "Physics"
    process_csv_to_jsonl(major,input_csv, output_jsonl)
   