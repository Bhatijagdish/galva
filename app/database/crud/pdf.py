from sqlalchemy.orm import Session
from database import PDF


def get_pdfs(db: Session, page: int, limit: int):
    skip = (page - 1) * limit
    return db.query(PDF).offset(skip).limit(limit).all()


def create_pdf(db: Session, filename: str):
    db_pdf = PDF(filename=filename)
    db.add(db_pdf)
    db.commit()
    db.refresh(db_pdf)
    return db_pdf


def delete_pdf(db: Session, pdf_id: int):
    db_pdf = db.query(PDF).filter(PDF.id == pdf_id).first()
    if db_pdf:
        db.delete(db_pdf)
        db.commit()
        return True
    return False


def get_pdf_by_id(db: Session, pdf_id: int):
    return db.query(PDF).filter(PDF.id == pdf_id).first()


def delete_pdf_by_filename(db: Session, pdf_filename: str):
    db_pdf = db.query(PDF).filter(PDF.filename == pdf_filename).first()
    if db_pdf:
        db.delete(db_pdf)
        db.commit()
        return True
    return False


def get_pdf_by_filename(db: Session, filename: str):
    return db.query(PDF).filter(PDF.filename == filename).first()
