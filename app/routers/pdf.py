import os
import shutil
from typing import List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from database import db_connection, create_pdf, delete_pdf, get_pdfs, get_pdf_by_filename, get_pdf_by_id, logger
from routers.user import get_current_admin_user
from routers.chat import ai

router = APIRouter()


@router.post("/upload_pdf")
async def upload_pdf(files: List[UploadFile] = File(...), db: Session = Depends(db_connection),
                     current_admin_user=Depends(get_current_admin_user)):
    file_name = None
    try:
        os.makedirs(ai.pdf_dir_path, exist_ok=True)
        saved_files = []
        for file in files:
            file_name = file.filename
            file_location = os.path.join(ai.pdf_dir_path, file_name)
            with open(file_location, "wb+") as file_object:
                shutil.copyfileobj(file.file, file_object)
            out_file = create_pdf(db, file_name)
            logger.info("Successfully added to the db")
            saved_files.append(out_file)
            ai.add_file_to_vector_store(file_location)
        return [file_name for file_name in saved_files]
    except Exception as e:
        return JSONResponse(content=f"File already exists {file_name}", status_code=400)


@router.get("/pdfs")
async def list_pdfs(skip: int = 0, limit: int = 100, db: Session = Depends(db_connection),
                    current_admin_user=Depends(get_current_admin_user)):
    pdfs = get_pdfs(db, skip, limit)
    return [pdf for pdf in pdfs]


@router.delete("/pdfs/{pdf_id}")
async def delete_pdf_route(pdf_id: int, db: Session = Depends(db_connection),
                           current_admin_user=Depends(get_current_admin_user)):
    try:
        pdf_record = get_pdf_by_id(db, pdf_id)
        if not pdf_record:
            return JSONResponse(status_code=404, content="PDF not found in the database")
        logger.info("pdf record found")
        if not delete_pdf(db, pdf_id):
            return JSONResponse(content=f"Unable to delete pdf record for {pdf_record.filename} file",
                                status_code=400)
        logger.info("pdf deleted successfully")
        file_location = os.path.join(ai.pdf_dir_path, pdf_record.filename)
        if os.path.exists(file_location):
            os.remove(file_location)
            logger.info("Deleted pdf from the directory")
            ai.delete_file_from_vector_store(file_location)
            logger.info("Deleted pdf from the vector store")
            return JSONResponse(content=f"File {pdf_record.filename} deleted from both upload "
                                        f"directory and vector database", status_code=200)
        else:
            return JSONResponse(status_code=404, content="File not found in the upload directory")

    except Exception as e:
        return JSONResponse(status_code=500, content=f"Error deleting file: {e}")


# @router.get("/pdfs/{pdf_filename}")
# async def retrieve_pdf_route(pdf_filename: str, db: Session = Depends(db_connection),
#                              current_admin_user=Depends(get_current_admin_user)):
#     try:
#         pdf_record = get_pdf_by_filename(db, pdf_filename)
#         if not pdf_record:
#             return JSONResponse(status_code=404, content="PDF not found in the database")
#         return pdf_record
#     except Exception as e:
#         return JSONResponse(status_code=400, content=f"Error deleting file: {e}")


@router.delete("/pdfs/file/{pdf_filename}")
async def delete_pdf_route(pdf_filename: str, db: Session = Depends(db_connection),
                           current_admin_user=Depends(get_current_admin_user)):
    try:
        pdf_record = get_pdf_by_filename(db, pdf_filename)
        if not pdf_record:
            return JSONResponse(status_code=404, content="PDF not found in the database")
        file_location = os.path.join(ai.pdf_dir_path, pdf_filename)
        if os.path.exists(file_location):
            os.remove(file_location)
        else:
            return JSONResponse(status_code=404, content="File not found in the upload directory")

        if delete_pdf(db, pdf_filename):
            file_location = os.path.join(ai.pdf_dir_path, pdf_filename)
            ai.delete_file_from_vector_store(file_location)
            return JSONResponse(content=f"File {pdf_record.filename} deleted from both upload "
                                        f"directory and vector database", status_code=200)
        else:
            return JSONResponse(content=f"Unable to delete pdf record for {pdf_record.filename} file",
                                status_code=400)
    except Exception as e:
        return JSONResponse(status_code=400, content=f"Error deleting file: {e}")


@router.get("/pdfs/{filename}")
async def get_pdf(filename: str):
    file_path = os.path.join(ai.pdf_dir_path, filename)
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content="File not found")
    return FileResponse(file_path)
