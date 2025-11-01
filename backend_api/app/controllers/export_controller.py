from fastapi import UploadFile, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Any, Dict
import io
import json

from ..services.excel_service import process_export
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
SAMPLE_RULES = DATA_DIR / "sample_test3.json"


async def sample_data() -> JSONResponse:
    if SAMPLE_RULES.exists():
        try:
            data = json.loads(SAMPLE_RULES.read_text(encoding="utf-8"))
            return JSONResponse(content=data)
        except Exception:
            raise HTTPException(status_code=500, detail="Failed reading sample rules file")
    return JSONResponse(content={"rules": []})


async def export_file(file: UploadFile, sheet: str) -> StreamingResponse:
    # Basic validation
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx/.xls) are supported")

    try:
        out_bytes, out_name = await process_export(file, sheet)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

    headers = {"Content-Disposition": f'attachment; filename="{out_name}"'}
    return StreamingResponse(io.BytesIO(out_bytes),
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers=headers)
