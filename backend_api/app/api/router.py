from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
from ..controllers.export_controller import sample_data, export_file

router = APIRouter()


@router.get("/sample-data")
async def _sample_data():
    return await sample_data()


@router.post("/export")
async def _export(file: UploadFile = File(...), sheet: str = Form(...)):
    return await export_file(file=file, sheet=sheet)

@router.post("/test")
async def _test(file: UploadFile = File(...)):
    return await export_file(file=file, sheet=sheet)
