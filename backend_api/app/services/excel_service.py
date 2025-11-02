from fastapi import UploadFile
from typing import Tuple, Dict, Any
from ..utils.excel_utils import read_excel_from_upload, dataframe_to_excel_bytes, normalize_dataframe
from ..services.llm_service import apply_rules_to_df
from pathlib import Path
import json

# Additional imports for table cleaning utilities
import io
import re
from typing import List, Optional
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"
SAMPLE_RULES = DATA_DIR / "sample3_test.json" 


async def process_export(file: UploadFile, sheet: str) -> Tuple[bytes, str]:
    """
    Read uploaded excel, apply rules (via LLM service), return bytes and filename.
    """
    # Read raw bytes once and try advanced detection/cleaning
    contents = await file.read()

    # Try to detect and clean tabular blocks per sheet using advanced heuristics
    try:
        cleaned_map = detect_and_clean_tables_from_bytes(contents)
    except Exception:
        cleaned_map = {}

    df = None
    if sheet in cleaned_map and cleaned_map[sheet]:
        # Use the first detected table for the requested sheet
        df = cleaned_map[sheet][0]
    else:
        # Fallback: read sheet and normalize using existing heuristics
        import io as _io
        try:
            with _io.BytesIO(contents) as b:
                xl = pd.ExcelFile(b)
                if sheet not in xl.sheet_names:
                    raise ValueError(f"Sheet '{sheet}' not found. Available: {xl.sheet_names}")
                raw_df = pd.read_excel(xl, sheet_name=sheet, header=None, engine="openpyxl")
                df = normalize_dataframe(raw_df)
        except ValueError:
            # re-raise sheet not found
            raise
        except Exception as e:
            raise ValueError(f"Failed reading sheet '{sheet}': {e}")

    # Load rules if available
    rules: Dict[str, Any] = {}
    print(f"Loading sample rules from {SAMPLE_RULES}")
    print(f"Existe: {SAMPLE_RULES.exists()}")
    if SAMPLE_RULES.exists():
        try:
            rules = json.loads(SAMPLE_RULES.read_text(encoding="utf-8"))
            print(f"Loaded sample rules from {SAMPLE_RULES}")
        except Exception:
            rules = {}

    # Apply rules
    out_sheets: Dict[str, pd.DataFrame] = {}
    if sheet in cleaned_map and cleaned_map[sheet]:
        # multiple detected tables -> apply rules to each and export as separate sheets
        for idx, tbl in enumerate(cleaned_map[sheet], start=1):
            name = f"{sheet}_Table{idx}"
            try:
                out_df = apply_rules_to_df(tbl, rules)
            except Exception:
                out_df = tbl
            out_sheets[name] = out_df
    else:
        # Single sheet fallback
        try:
            new_df = apply_rules_to_df(df, rules)
        except Exception:
            new_df = df
        out_sheets[sheet] = new_df

    # Write back to excel bytes (may contain multiple sheets)
    out_bytes = dataframe_to_excel_bytes(out_sheets)

    out_name = f"modified_{file.filename}"
    return out_bytes, out_name


# -------------------------
# Table cleaning utilities (ported/adapted from test/test.py)
# -------------------------


def slugify_header(s) -> str:
    """Convert header-like values to a safe snake_case string.

    Preserves behavior when encountering None / NaN.
    """
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return "unnamed"
    s = str(s).strip()
    s = re.sub(r"[^\w]+", "_", s, flags=re.UNICODE).strip("_").lower()
    return s or "unnamed"


def trim_edges(df: pd.DataFrame) -> pd.DataFrame:
    """Trim fully-empty rows/columns from the four edges of the DataFrame."""
    out = df.copy()
    # Top
    while len(out) and out.isna().all(axis=1).iloc[0]:
        out = out.iloc[1:, :]
    # Bottom
    while len(out) and out.isna().all(axis=1).iloc[-1]:
        out = out.iloc[:-1, :]
    # Left
    while out.shape[1] and out.isna().all(axis=0).iloc[0]:
        out = out.iloc[:, 1:]
    # Right
    while out.shape[1] and out.isna().all(axis=0).iloc[-1]:
        out = out.iloc[:, :-1]
    return out


def find_segments(non_null_counts: List[int],
                  min_non_null: int = 2,
                  min_rows: int = 2) -> List[tuple]:
    """Find contiguous segments (inclusive ranges) where rows have at least `min_non_null` non-empty cells.

    Returns a list of (start_idx, end_idx) pairs.
    """
    good = [i for i, c in enumerate(non_null_counts) if c >= min_non_null]
    if not good:
        return []
    segs = []
    start = prev = good[0]
    for r in good[1:]:
        if r == prev + 1:
            prev = r
        else:
            if prev - start + 1 >= min_rows:
                segs.append((start, prev))
            start = prev = r
    if prev - start + 1 >= min_rows:
        segs.append((start, prev))
    return segs


def clean_block(block: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Clean a candidate block (table) extracted from an Excel sheet.

    Steps:
    - Trim empty edges
    - Detect header row
    - Normalize headers
    - Drop empty cols/rows
    - Try numeric conversion
    """
    block = trim_edges(block)
    if block.empty:
        return None

    # Header row: first row with >= 2 non-empty cells, default 0
    header_idx = next((i for i in range(len(block)) if block.iloc[i].notna().sum() >= 2), 0)
    cols = [slugify_header(x) for x in block.iloc[header_idx].tolist()]
    data = block.iloc[header_idx + 1 :].copy()
    if data.shape[0] == 0:
        return None

    # Trim or extend columns to match header length
    data = data.iloc[:, : len(cols)]
    data.columns = cols

    # Drop fully-empty or blank-only columns
    keep_cols = []
    for c in data.columns:
        col = data[c]
        if not (col.isna().all() or (col.astype(str).str.strip() == "").all()):
            keep_cols.append(c)
    data = data[keep_cols]
    if data.shape[1] == 0:
        return None

    # Drop empty rows
    mask_empty_row = data.isna().all(axis=1) | data.astype(str).apply(lambda x: x.str.strip()).eq("").all(axis=1)
    data = data.loc[~mask_empty_row].reset_index(drop=True)
    if data.empty:
        return None

    # Try to convert numeric-ish columns
    for c in data.columns:
        data[c] = pd.to_numeric(data[c], errors="ignore")

    return data


def detect_and_clean_tables_from_bytes(excel_bytes: bytes,
                                       min_non_null: int = 2,
                                       min_rows: int = 2) -> Dict[str, List[pd.DataFrame]]:
    """Read an Excel file from bytes and detect/clean tabular blocks per sheet.

    Returns a dict: {sheet_name: [cleaned_table_df, ...], ...}
    """
    out: Dict[str, List[pd.DataFrame]] = {}
    with io.BytesIO(excel_bytes) as b:
        sheets = pd.read_excel(b, sheet_name=None, header=None, engine="openpyxl")

    for sheet_name, df in sheets.items():
        df = trim_edges(df)
        if df.empty:
            continue

        non_null_counts = df.notna().sum(axis=1).tolist()
        segs = find_segments(non_null_counts, min_non_null=min_non_null, min_rows=min_rows)
        if not segs:
            segs = [(0, len(df) - 1)]

        cleaned_tables: List[pd.DataFrame] = []
        for (r0, r1) in segs:
            block = df.iloc[r0 : r1 + 1, :]
            cleaned = clean_block(block)
            if cleaned is None or cleaned.empty:
                continue
            cleaned_tables.append(cleaned)

        if cleaned_tables:
            out[sheet_name] = cleaned_tables

    return out


__all__ = [
    "slugify_header",
    "trim_edges",
    "find_segments",
    "clean_block",
    "detect_and_clean_tables_from_bytes",
]
