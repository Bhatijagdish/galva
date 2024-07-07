from google.api_core.client_options import ClientOptions
from google.cloud import documentai
import os
import logging


def process_pdf(file_path: str):
    try:
        PROJECT_ID = os.getenv("PROJECT_ID", "pdf-chatbot-411714")
        LOCATION = os.getenv("LOCATION", "us")
        PROCESSOR_ID = os.getenv("PROCESSOR_ID", "de04712cbef94f7d")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS",
                                                                 "env/pdf-chatbot-admin.json")
        MIME_TYPE = "application/pdf"

        docai_client = documentai.DocumentProcessorServiceClient(
            client_options=ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
        )
        RESOURCE_NAME = docai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

        with open(file_path, "rb") as image:
            image_content = image.read()

        raw_document = documentai.RawDocument(content=image_content, mime_type=MIME_TYPE)
        request = documentai.ProcessRequest(name=RESOURCE_NAME, raw_document=raw_document)
        result = docai_client.process_document(request=request)

        logging.info(f'OCR: {file_path}')
        return result.document.text
    except Exception as e:
        logging.error(f"Error in process_pdf: {e}")
        raise
