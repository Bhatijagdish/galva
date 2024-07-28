import logging
import shutil

import jwt
from jwt import PyJWTError as JWTError
from datetime import datetime, timedelta
import os
import bcrypt
import pandas as pd
from logging.handlers import RotatingFileHandler
import smtplib
from email.mime.text import MIMEText


class Settings:
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY",
                                "1f262fd466d436d2a51910bdb79cdcfa7ba85c76f84508818687fdb175514d84")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60


salt = bcrypt.gensalt()

settings = Settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed__password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed__password.encode('utf-8'))


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def store_to_df(store):
    v_dict = store.docstore._dict
    data_rows = []
    for k in v_dict.keys():
        logging.info(v_dict[k])
        doc_name = v_dict[k].metadata['source'].split('/')[-1]
        content = v_dict[k].page_content
        data_rows.append({"chunk_id": k, "document": doc_name, "content": content})
    vector_df = pd.DataFrame(data_rows)
    return vector_df


# def driver(root_folder, vector_path):
#     try:
#         combined_output_dir = os.path.join(root_folder, "combined_outputs")
#
#         # Delete the combined_outputs directory if it exists
#         if os.path.exists(combined_output_dir):
#             shutil.rmtree(combined_output_dir)
#
#         # Create combined output directory
#         os.makedirs(combined_output_dir)
#
#         # Process each PDF file in the root folder
#         for file_name in os.listdir(root_folder):
#             if file_name.endswith(".pdf"):
#                 file_path = os.path.join(root_folder, file_name)
#                 process_and_combine(file_path, combined_output_dir)
#
#         # Create a temporary directory for vectorDB2
#         temp_dir = tempfile.mkdtemp()
#         vectorDB2_path = os.path.join(temp_dir, "vectorDB2")
#
#         # Process the combined documents
#         process1_docs(combined_output_dir, vectorDB2_path)
#
#         # Merge the vector databases
#         first_merge(vectorDB1_path, vectorDB2_path)
#
#         # Cleanup temporary directory
#         shutil.rmtree(temp_dir)
#
#         # Transfer all PDFs from the root folder ("pdfs") to "./data/processed_pdfs"
#         processed_pdf_dir = os.path.join("app/data", "processed_pdfs")
#         if not os.path.exists(processed_pdf_dir):
#             os.makedirs(processed_pdf_dir)
#
#         for file_name in os.listdir(root_folder):
#             if file_name.endswith(".pdf"):
#                 src_path = os.path.join(root_folder, file_name)
#                 dest_path = os.path.join(processed_pdf_dir, file_name)
#                 shutil.move(src_path, dest_path)
#         # Delete everything in the root_folder
#         for item in os.listdir(root_folder):
#             item_path = os.path.join(root_folder, item)
#             if os.path.isdir(item_path):
#                 shutil.rmtree(item_path)
#             else:
#                 os.remove(item_path)
#         logging.info("Processing complete!")
#         return "Processing complete!"
#     except Exception as e:
#         logging.error(f"Error in driver: {e}")
#         raise


def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler('tas.log', maxBytes=1024 * 1024 * 10, backupCount=3)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def send_email(to_email: str, subject: str, html_content: str,
               sender_email: str, sender_email_password: str):
    msg = MIMEText(html_content, "html")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, sender_email_password)
        server.sendmail(sender_email, to_email, msg.as_string())
