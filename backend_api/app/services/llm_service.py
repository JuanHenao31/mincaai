from typing import Dict, Any, Optional
import pandas as pd
import os
import re
import io
import time
from pathlib import Path
from datetime import datetime
import logging


# Prompts (adapted from test/llm.py)
PROMPT_SYSTEM = """Eres un transformador de datos ESTRICTO.
Debes seguir las instrucciones que te paso en formato JSON.
Tu salida DEBE ser únicamente un CSV válido (con encabezado) que represente el resultado final.
No escribas texto adicional, ni JSON, ni explicaciones. Solo el CSV limpio.
"""

PROMPT_USER_TEMPLATE = """Instrucciones (pueden cambiar, sigue SOLO esto):
{instructions_json}

Contexto:
- A continuación tienes una hoja del Excel fuente (en formato CSV).
- Debes transformarla según las reglas y formato final indicados en las instrucciones.
- Devuelve el CSV resultante con las columnas finales en el orden correcto.
- Si falta un dato, deja la celda vacía. No agregues comentarios.

HOJA DE ENTRADA ({sheet_name}):

{csv_content}


Recuerda:
- Devuelve ÚNICAMENTE el CSV final (con encabezado).
- Nada de explicaciones ni texto extra.
- IMPORTANTE: Algunos valores (por ejemplo en la columna `descripcion`) pueden contener comas como separador de miles (ej. "31,500 LTS"). Para evitar que el CSV quede mal formado, haz una de las dos cosas (preferencia 1):
    1) Reemplaza TODAS las comas internas dentro del campo `descripcion` por puntos (.) — ej. "31,500 LTS" -> "31.500 LTS" — y asegúrate de que el CSV resultante tenga el mismo número de columnas en todas las filas.
    2) Si prefieres no reemplazar, encierra entrecomillado DOBLE (") cualquier campo que pueda contener comas.

El objetivo es que el CSV devuelto sea válido y pueda ser leído por pandas.read_csv sin causar errores de tokenización.
"""



def _sanitize_llm_text_to_csv(text: str) -> str:
    """Try to extract a CSV block from arbitrary model output.

    This removes markdown fences and extracts the first plausible CSV-looking block.
    """
    if not text:
        return ""
    # Remove code fences
    text = re.sub(r"^\s*```[\w\W]*?```\s*$", lambda m: m.group(0).strip('`'), text, flags=re.M)
    # Remove triple-backtick blocks more robustly
    text = re.sub(r"```(?:[\s\S]*?)```", lambda m: m.group(0).strip('`'), text)

    # Find first line that looks like a CSV header (contains at least one comma)
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if "," in ln:
            start = i
            break
    if start is None:
        # fallback: return original text
        return text.strip()

    # Collect from start until a long run of blank lines or end
    csv_lines = []
    for ln in lines[start:]:
        # stop if we see a line that is very unlikely to be CSV (no commas and not empty) and follows several similar
        csv_lines.append(ln)

    csv_text = "\n".join(csv_lines).strip()
    return csv_text


def _call_openai_csv(system_prompt: str, user_prompt: str, model: str = "gpt-4o-mini",
                     max_retries: int = 2, timeout: int = 30) -> str:
    """Call OpenAI ChatCompletion and expect text output containing a CSV.

    Retries on failure with small backoff. Raises if unable to call.
    """
    try:
        # lazy import to keep module import safe when openai not installed
        import openai
    except Exception:
        raise RuntimeError("openai package not available")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    openai.api_key = api_key

    attempt = 0
    last_err = None
    while attempt <= max_retries:
        try:
            from openai import OpenAI

            # instantiate client with API key from environment (validated above)
            client = OpenAI(api_key=api_key)

            resp = client.chat.completions.create(
                model=model,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                timeout=timeout,
            )
            text = resp.choices[0].message.content
            return text
        except Exception as e:
            last_err = e
            attempt += 1
            time.sleep(1 + attempt * 0.5)
    raise last_err


def _mock_apply_rules(df: pd.DataFrame, rules: Dict[str, Any]) -> pd.DataFrame:
    """Deterministic fallback used when LLM is not available or fails.

    This preserves existing heuristic logic previously implemented in apply_rules_to_df.
    """
    df = df.copy()

    # find candidate column that describes unit type
    col_candidates = [c for c in df.columns if c and str(c).lower() in ("unidad", "unit_type", "tipo_unidad", "tipo")]
    unit_col = col_candidates[0] if col_candidates else None

    def infer_limits(u):
        if pd.isna(u):
            return "25000"
        try:
            s = str(u).lower()
        except Exception:
            return "25000"
        if "camion" in s or "truck" in s:
            return "100000"
        if "auto" in s or "car" in s or "vehiculo" in s:
            return "50000"
        return "25000"

    if unit_col:
        df["DANOS MATERIALES LIMITES"] = df[unit_col].apply(infer_limits)
        df["ROBO TOTAL LIMITES"] = df[unit_col].apply(infer_limits)
    else:
        df["DANOS MATERIALES LIMITES"] = "VALOR CONVENIDO"
        df["ROBO TOTAL LIMITES"] = "VALOR CONVENIDO"

    # Deductibles heuristic: fallback to rules dict if present
    try:
        # rules may contain mapping per unit type in a nested structure
        if isinstance(rules, dict) and "coberturas_por_tipo" in rules:
            def ded_for_unit(unit, key):
                try:
                    tu = str(unit).upper()
                except Exception:
                    tu = ""
                for k, v in rules.get("coberturas_por_tipo", {}).items():
                    if k in tu or k in str(unit):
                        cov = v.get("coberturas", {})
                        item = cov.get(key, {})
                        return item.get("DEDUCIBLES") or item.get("DEDUCIBLES", "")
                return ""

            if unit_col:
                df["DANOS MATERIALES DEDUCIBLES"] = df[unit_col].apply(lambda u: ded_for_unit(u, "DANOS MATERIALES") or "10 %")
                df["ROBO TOTAL DEDUCIBLES"] = df[unit_col].apply(lambda u: ded_for_unit(u, "ROBO TOTAL") or "10 %")
            else:
                df["DANOS MATERIALES DEDUCIBLES"] = "10 %"
                df["ROBO TOTAL DEDUCIBLES"] = "10 %"
    except Exception:
        df["DANOS MATERIALES DEDUCIBLES"] = "10 %"
        df["ROBO TOTAL DEDUCIBLES"] = "10 %"

    return df


def transform_sheet_with_rules(df: pd.DataFrame, rules: Dict[str, Any], model: Optional[str] = None,
                               use_llm: bool = True, timeout: int = 30) -> pd.DataFrame:
    """Transform a single DataFrame (sheet) according to rules.

    Tries to use the LLM to produce a CSV-only response. If that fails or OPENAI_API_KEY
    is missing, falls back to deterministic `_mock_apply_rules`.
    """
    df = df.copy()

    openai_key = os.getenv("OPENAI_API_KEY")
    if use_llm and openai_key:
        csv_content = df.to_csv(index=False)
        # inline import to avoid heavy deps at import time
        import json
        logger = logging.getLogger(__name__)
        user_prompt = PROMPT_USER_TEMPLATE.format(instructions_json=(rules and json.dumps(rules, ensure_ascii=False) or ""),
                                                  csv_content=csv_content,
                                                  sheet_name="sheet")
        raw = None
        try:
            raw = _call_openai_csv(PROMPT_SYSTEM, user_prompt, model=(model or "gpt-4o-mini"), timeout=timeout)
            csv_text = _sanitize_llm_text_to_csv(raw)
            out_df = pd.read_csv(io.StringIO(csv_text))
            return out_df
        except Exception as e:
            # Save raw output for debugging if available
            try:
                BASE_DIR = Path(__file__).resolve().parents[2]
                debug_dir = BASE_DIR / "data" / "llm_debug"
                debug_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                fname = debug_dir / f"llm_raw_{timestamp}.txt"
                with open(fname, "w", encoding="utf-8") as fh:
                    if raw:
                        fh.write(raw)
                    else:
                        fh.write(user_prompt)
                        fh.write("\n\n--ERROR: \n")
                        fh.write(str(e))
                logger.exception("LLM transform failed; raw output saved to %s", str(fname))
            except Exception:
                # If saving fails, just log
                logger.exception("Failed saving LLM raw output for debugging")
            # On any failure, move to fallback deterministic rules
            pass

    # As last resort, deterministic mock
    return _mock_apply_rules(df, rules)


def apply_rules_to_df(df: pd.DataFrame, rules: Dict[str, Any]) -> pd.DataFrame:
    """Public wrapper kept for backward compatibility. Uses transform_sheet_with_rules."""
    return transform_sheet_with_rules(df, rules, use_llm=True)
