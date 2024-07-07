import os
import logging
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from pypdf import PdfReader, PdfWriter
from google.api_core.client_options import ClientOptions
from google.cloud import documentai
import tempfile
import shutil
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Program 1: Split PDF page wise
def split_pdf(file_path, pages_per_file=1):
    try:
        pdf = PdfReader(file_path)
        total_pages = len(pdf.pages)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_files = []

        # Create a directory called 'temp' if it doesn't exist
        temp_dir = 'temp'
        os.makedirs(temp_dir, exist_ok=True)

        for start_page in range(0, total_pages, pages_per_file):
            end_page = min(start_page + pages_per_file - 1, total_pages - 1)
            pdf_writer = PdfWriter()

            for page in range(start_page, end_page + 1):
                pdf_writer.add_page(pdf.pages[page])

            output_filename = os.path.join(temp_dir, f"{base_name}pages{start_page + 1}to{end_page + 1}.pdf")
            output_files.append(output_filename)

            with open(output_filename, 'wb') as out:
                pdf_writer.write(out)

            logging.info(f'Created: {output_filename}')

        return output_files, temp_dir
    except Exception as e:
        logging.error(f"Error in split_pdf: {e}")
        raise


# Program 2: do OCR with Document AI
def process_pdf(file_path):
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


# Combine OCR text to PDF
def process_and_combine(file_path, output_dir, pages_per_file=1):
    try:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file_path = os.path.join(output_dir, f"{base_name}.pdf")

        split_files, temp_dir = split_pdf(file_path, pages_per_file)
        combined_text = ""
        i = 1
        doc = SimpleDocTemplate(output_file_path)
        story = []
        styles = getSampleStyleSheet()

        for split_file in split_files:
            text = process_pdf(split_file)
            combined_text = "Page number: " + str(i) + "\n" + text + "\n"
            story.append(Paragraph(combined_text, styles["BodyText"]))
            story.append(PageBreak())
            i += 1

        doc.build(story)
        logging.info(f"Created: {output_file_path}")

        # Delete temporary files and directory
        for split_file in split_files:
            os.remove(split_file)
        os.rmdir(temp_dir)
    except Exception as e:
        logging.error(f"Error in process_and_combine: {e}")
        raise


# Process Documents to vector
def process1_docs(input_dir, output_dir):
    try:
        from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
        from langchain_community.vectorstores import FAISS
        from langchain_openai import OpenAIEmbeddings
        from langchain.text_splitter import RecursiveCharacterTextSplitter

        loader1 = DirectoryLoader(input_dir, glob="./*.pdf", loader_cls=PyPDFLoader)
        document1 = loader1.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )

        docs = text_splitter.split_documents(document1)
        for doc in docs:
            # Extract the source path
            source_path = doc.metadata['source']

            # Extract just the file name
            file_name = os.path.basename(source_path)

            # Update the dictionary
            doc.metadata['source'] = file_name

        embeddings = OpenAIEmbeddings()
        # change to just name of file remove the path

        docs_db = FAISS.from_documents(docs, embeddings)
        docs_db.save_local(output_dir)

        return "Successful!"
    except Exception as e:
        logging.error(f"Error in process1_docs: {e}")
        raise


# Merge Vector Databases
def first_merge(vectorDB1_path, vectorDB2_path):
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_openai import OpenAIEmbeddings

        embeddings = OpenAIEmbeddings()
        docs_db1 = FAISS.load_local(vectorDB1_path, embeddings)
        docs_db2 = FAISS.load_local(vectorDB2_path, embeddings)
        docs_db2.merge_from(docs_db1)
        docs_db2.save_local(vectorDB1_path)
        return "Successful!"
    except Exception as e:
        logging.error(f"Error in first_merge: {e}")
        raise


# Driver Function
def driver(root_folder, vectorDB1_path):
    try:
        combined_output_dir = os.path.join(root_folder, "combined_outputs")

        # Delete the combined_outputs directory if it exists
        if os.path.exists(combined_output_dir):
            shutil.rmtree(combined_output_dir)

        # Create combined output directory
        os.makedirs(combined_output_dir)

        # Process each PDF file in the root folder
        for file_name in os.listdir(root_folder):
            if file_name.endswith(".pdf"):
                file_path = os.path.join(root_folder, file_name)
                process_and_combine(file_path, combined_output_dir)

        # Create a temporary directory for vectorDB2
        temp_dir = tempfile.mkdtemp()
        vectorDB2_path = os.path.join(temp_dir, "vectorDB2")

        # Process the combined documents
        process1_docs(combined_output_dir, vectorDB2_path)

        # Merge the vector databases
        first_merge(vectorDB1_path, vectorDB2_path)

        # Cleanup temporary directory
        shutil.rmtree(temp_dir)

        # Transfer all PDFs from the root folder ("pdfs") to "./data/processed_pdfs"
        processed_pdf_dir = os.path.join("app/data", "processed_pdfs")
        if not os.path.exists(processed_pdf_dir):
            os.makedirs(processed_pdf_dir)

        for file_name in os.listdir(root_folder):
            if file_name.endswith(".pdf"):
                src_path = os.path.join(root_folder, file_name)
                dest_path = os.path.join(processed_pdf_dir, file_name)
                shutil.move(src_path, dest_path)
        # Delete everything in the root_folder
        for item in os.listdir(root_folder):
            item_path = os.path.join(root_folder, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        logging.info("Processing complete!")
        return "Processing complete!"
    except Exception as e:
        logging.error(f"Error in driver: {e}")
        raise

# Todo delete combined output folder 
# make a seperate folder to view uploaded pdfs
# also ensure that u just keep the file name

# driver("D:\Projects\Galva AI\chatbot\data\pdfs","data\merged_vector")
