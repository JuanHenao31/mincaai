import io

import pandas as pd

from backend_api.app.services import excel_service


def test_clean_block_basic():
    # Build a DataFrame that has empty top row, header row at index 1 and two data rows
    data = [
        [None, None, None],
        ["Header1", "Header2", None],
        ["a", "1", None],
        ["b", "2", None],
        [None, None, None],
    ]
    df = pd.DataFrame(data)

    cleaned = excel_service.clean_block(df)
    assert cleaned is not None
    # headers should be slugified to snake_case lowercase
    assert list(cleaned.columns) == ["header1", "header2"]
    # two data rows
    assert cleaned.shape[0] == 2
    assert cleaned.iloc[0]["header1"] == "a"
    # numeric conversion should have happened for numeric-looking column
    assert str(cleaned.iloc[0]["header2"]) == "1"


def test_detect_and_clean_tables_from_bytes_basic():
    # Create an in-memory Excel with one sheet that contains a table surrounded by empty rows
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # sheet1: table with empty rows
        sheet1 = pd.DataFrame([
            [None, None, None],
            ["H A", "H B", None],
            ["x1", 10, None],
            ["x2", 20, None],
            [None, None, None],
        ])
        sheet1.to_excel(writer, index=False, header=False, sheet_name="Sheet1")

        # sheet2: mostly empty
        sheet2 = pd.DataFrame([[None, None], [None, None]])
        sheet2.to_excel(writer, index=False, header=False, sheet_name="EmptySheet")

    buf.seek(0)
    excel_bytes = buf.getvalue()

    result = excel_service.detect_and_clean_tables_from_bytes(excel_bytes)
    assert "Sheet1" in result
    tables = result["Sheet1"]
    assert isinstance(tables, list)
    assert len(tables) == 1
    t0 = tables[0]
    # header names should be slugified
    assert list(t0.columns) == ["h_a", "h_b"]
    # two rows expected
    assert t0.shape[0] == 2
