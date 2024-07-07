from pydantic import BaseModel


class PdfBaseModel(BaseModel):
    id: int
    filename: str


class PdfUploadModel(BaseModel):
    filename: str
