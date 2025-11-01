import os
import json
from typing import Any
import pandas as pd

try:
    import openai
except Exception:
    openai = None


def call_openai_for_enrichment(df: pd.DataFrame, rules: Any) -> Any:
    """
    Call OpenAI to enrich data. Expects OPENAI_API_KEY in env and openai package installed.
    Returns either a DataFrame or a list of dicts representing rows.
    This is a small wrapper that builds a prompt and requests JSON output.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    if openai is None:
        raise RuntimeError("openai package not available")

    openai.api_key = api_key

    # Prepare small sample of data to include in prompt
    sample_rows = df.head(50).to_dict(orient="records")
    prompt = (
        "You are a data transformation assistant.\n"
        "Given a JSON rule set and a list of rows, apply the rules and return the updated rows as JSON array.\n"
        "Rules: " + json.dumps(rules) + "\n"
        "Rows: " + json.dumps(sample_rows, default=str) + "\n"
        "Return only valid JSON: an array of row objects with the same or new columns. Do not include any explanatory text."
    )

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1500,
        )
        text = resp.choices[0].message.content
        # parse JSON
        parsed = json.loads(text)
        # If parsed is list of dicts, try convert to DataFrame
        if isinstance(parsed, list):
            return pd.DataFrame(parsed)
        return parsed
    except Exception as e:
        # bubble up to caller
        raise
