import pandas as pd
from fastapi import UploadFile
import io
from typing import Dict


async def read_excel_from_upload(file: UploadFile, sheet: str) -> pd.DataFrame:
    """
    Read the requested sheet from an uploaded Excel file (UploadFile).
    Raises ValueError if sheet not found.

    This function reads the sheet without inferring headers so we can detect and
    normalize the header row (promote header), drop empty rows/columns and trim strings.
    """
    contents = await file.read()
    with io.BytesIO(contents) as b:
        xl = pd.ExcelFile(b)
        if sheet not in xl.sheet_names:
            raise ValueError(f"Sheet '{sheet}' not found. Available sheets: {xl.sheet_names}")
        df = pd.read_excel(xl, sheet_name=sheet, header=None, dtype=object)
        df = normalize_dataframe(df)
        return df


def dataframe_to_excel_bytes(sheets: Dict[str, pd.DataFrame]) -> bytes:
    """
    Given a dict of {sheet_name: DataFrame}, return bytes of an .xlsx file.
    """
    with io.BytesIO() as out:
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            for name, df in sheets.items():
                df.to_excel(writer, sheet_name=name[:31], index=False)
        return out.getvalue()


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Heuristics to normalize Excel sheets:
    - Drop fully empty rows and columns
    - Detect header row (first row among first N with >= half non-empty cells)
    - Promote that row to columns, remove preceding rows
    - Drop 'Unnamed' or empty column names
    - Trim string cells
    - Remove obvious summary rows (e.g., rows with 'TOTAL', 'RESUMEN') when they look like totals
    """
    df = df.copy()
    # Drop fully empty rows/cols
    df = df.dropna(axis=0, how='all')
    df = df.dropna(axis=1, how='all')

    if df.empty:
        return df

    # Work with a limited prefix to find header
    max_header_scan = min(10, len(df))
    header_row_idx = None
    col_count = df.shape[1]
    threshold = max(1, col_count // 2)

    for i in range(max_header_scan):
        non_null = df.iloc[i].notna().sum()
        if non_null >= threshold:
            header_row_idx = i
            break

    if header_row_idx is None:
        header_row_idx = 0

    # Use the header row values as column names
    raw_cols = df.iloc[header_row_idx].tolist()
    new_cols = []
    seen = {}
    for c in raw_cols:
        name = str(c).strip() if not pd.isna(c) else ""
        if not name:
            name = ""
        # make unique
        base = name or "col"
        cnt = seen.get(base, 0)
        seen[base] = cnt + 1
        if cnt > 0:
            name = f"{base}_{cnt}"
        new_cols.append(name)

    df = df.iloc[header_row_idx + 1 :].reset_index(drop=True)
    df.columns = new_cols

    # Drop columns with empty names or 'Unnamed'
    keep_mask = [bool(c and not str(c).lower().startswith("unnamed")) for c in df.columns]
    df = df.loc[:, keep_mask]

    # Drop columns that are entirely empty after that
    df = df.dropna(axis=1, how='all')

    # Trim whitespace in string cells
    df = df.applymap(lambda v: v.strip() if isinstance(v, str) else v)

    # Remove obvious summary rows
    keywords = ("total", "resumen", "subtotal", "desglose", "resumen")
    def is_summary_row(row):
        non_null = row.notna().sum()
        # if row contains any keyword and is relatively sparse, consider it summary
        for v in row.tolist():
            try:
                s = str(v).strip().lower()
            except Exception:
                s = ""
            if any(k in s for k in keywords):
                if non_null <= max(3, int(0.25 * col_count)):
                    return True
        return False

    mask = df.apply(lambda r: not is_summary_row(r), axis=1)
    df = df.loc[mask].reset_index(drop=True)

    # Drop fully empty rows again if any
    df = df.dropna(axis=0, how='all').reset_index(drop=True)

    return df
