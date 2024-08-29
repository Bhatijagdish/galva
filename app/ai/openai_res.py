import json
import os
from typing import Any
import asyncio
import openai
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.agents import AgentType, initialize_agent
from langchain.chat_models import ChatOpenAI

from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks.streaming_aiter import AsyncIteratorCallbackHandler
from langchain.schema import LLMResult
from langchain.embeddings import OpenAIEmbeddings

from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from database import logger, insert_message
from openai import OpenAI

load_dotenv()
client = OpenAI()


class AsyncCallbackHandler(AsyncIteratorCallbackHandler):
    content: str = ""
    final_answer: bool = False

    def __init__(self, db, session_id, history_id, user_id) -> None:
        super().__init__()
        self.db = db
        self.session_id = session_id
        self.history_id = history_id
        self.user_id = user_id
        self.ai_answer = ""

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        self.ai_answer += token
        self.content += token
        if self.final_answer:
            if '"action_input": "' in self.content:
                if token not in ['"', "}"]:
                    self.queue.put_nowait(token)
        elif "Final Answer" in self.content:
            self.final_answer = True
            self.content = ""

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        if self.final_answer:
            self.content = ""
            self.final_answer = False
            self.done.set()
            await self.save_to_db()
        else:
            self.content = ""

    async def save_to_db(self):
        # update the final ai answer here
        actual_answer = json.loads(str(self.ai_answer)[8:-4]).get("action_input")
        insert_message(self.db, self.session_id, self.history_id, 'ai', actual_answer, self.user_id)


class ConversationalAI:

    def __init__(self, pdf_dir_path: str = "pdfs", vector_db_path: str = "merged_vector",
                 model_name: str = "gpt-4o"):
        self.vector_path = os.path.join(os.getcwd(), "data", vector_db_path)
        self.pdf_dir_path = os.path.join(os.getcwd(), "data", pdf_dir_path)
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        self.embeddings = OpenAIEmbeddings()
        # Delete and replace local vector store files
        os.makedirs(self.vector_path, exist_ok=True)
        os.makedirs(self.pdf_dir_path, exist_ok=True)
        index_faiss = os.path.join(self.vector_path, "index.faiss")
        index_pkl = os.path.join(self.vector_path, "index.pkl")
        if os.path.exists(index_faiss):
            logger.info("Deleting index.faiss file...")
            os.remove(index_faiss)
        if os.path.exists(index_pkl):
            logger.info("Deleting index.pkl file...")
            os.remove(index_pkl)

        if os.listdir(self.pdf_dir_path):
            logger.info("Creating new vector store")
            self.create_vector_store()

        # self.vector_store()
        self.vector_db = None
        if os.path.exists(index_faiss):
            self.vector_db = FAISS.load_local(self.vector_path, self.embeddings, allow_dangerous_deserialization=True)
        self.model = model_name
        self.PREFIX = "You are fined tuned AI model (not from OpenAI) specially designed to answer various questions " \
                      "related to Electroplating. You will think step by step and answer the questions accurately. " \
                      "You will give correct chemical equations where it is necessary. " \
                      "Please mention any formula you use to solve the problem. " \
                      "Ensure your answer is detailed and will help potential users answer their queries. " \
                      "Answer the Question in the Language it is asked. " \
                      "Please ask for additional clarifications if you are confused or do not have all the " \
                      "information. Please give me an answer in proper Markdown. \n\n" \
                      "If the answer asked or provided in a table format then use the table html format." \
                      "For example:\n" \
                      "<table><thead><tr><th>Feature</th><th>Carbon (C)</th><th>Sodium Chloride (NaCl)</th>" \
                      "</tr></thead><tbody><tr><td><strong>Chemical Formula</strong></td><td>C</td>" \
                      "<td>NaCl</td></tr><tr><td><strong>Type of Substance</strong></td><td>Element</td>" \
                      "<td>Ionic Compound</td></tr></tbody></table>\n\n" \
                      "If the answer contains the chemical compound information then it should have html " \
                      "format for compound information. For example: <p>H<sub>2</sub>SO<sub>4</sub></p> \n" \
                      "If the answer asked about the chemical compound then the response should be correctly " \
                      "formatted. For example: <p>H<sub>2</sub>SO<sub>4</sub></p> for sulphuric acid etc."

        self.agent = self.create_agent()

    def create_vector_store(self):
        loader = PyPDFDirectoryLoader(self.pdf_dir_path)
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        split_docs = text_splitter.split_documents(docs)
        vector_store = FAISS.from_documents(split_docs, self.embeddings)
        vector_store.save_local(self.vector_path)

    def add_file_to_vector_store(self, pdf_file_name: str):
        loader = PyPDFLoader(pdf_file_name)
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        split_docs = text_splitter.split_documents(docs)
        vector_store = FAISS.from_documents(split_docs, self.embeddings)
        if self.vector_db is None:
            vector_store.save_local(self.vector_path)
            self.vector_db = FAISS.load_local(self.vector_path, self.embeddings, allow_dangerous_deserialization=True)
        else:
            self.vector_db.merge_from(vector_store)
            self.vector_db.save_local(self.vector_path)
        logger.info(f"{pdf_file_name} added to the vector store")

    def delete_file_from_vector_store(self, pdf_file_name: str):
        doc_ids = []
        for id, values in self.vector_db.docstore._dict.items():
            if pdf_file_name == values.metadata["source"]:
                doc_ids.append(id)
        self.vector_db.delete(doc_ids)
        logger.info(f"{pdf_file_name} deleted from the vector store")

    def create_agent(self):
        llm = ChatOpenAI(
            model_name=self.model,
            max_tokens=4000,
            temperature=0.7,
            streaming=True,  # ! important
            callbacks=[]  # ! important (but we will add them later)
        )
        memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            k=5,
            return_messages=True,
            output_key="output"
        )
        return initialize_agent(
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            llm=llm,
            tools=[],
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3,
            early_stopping_method="generate",
            memory=memory,
            return_intermediate_steps=False
        )

    async def run_call(self, query: str, chat_history: list, stream_it: AsyncCallbackHandler):
        ai_resp = user_resp = ""
        if chat_history:
            for msg in chat_history:
                if msg.sender.upper() == 'AI':
                    ai_resp += f"{msg.message_text}\n\n"

        all_content = ""
        if self.vector_db is not None:
            docs = self.vector_db.similarity_search(query)
            all_content = '\n'.join(doc.page_content for doc in docs)
        input_query = f"INFO: {self.PREFIX}\n" \
                      f"Main question is : {query}\n" \
                      f"This is the context: {all_content}\n{ai_resp}"

        self.agent.agent.llm_chain.llm.callbacks = [stream_it]

        await self.agent.acall(inputs={"input": input_query})

    async def run_call_no_rag(self, query: str, chat_history: list, stream_it: AsyncCallbackHandler):
        ai_resp = user_resp = ""
        if chat_history:
            for sender, message_text in chat_history:
                if sender.upper() == 'AI':
                    ai_resp += f"{message_text}\n\n"

        input_query = f"INFO: {self.PREFIX}\n" \
                      f"Main question is : {query}\n\n" \
                      f"This is the context: {ai_resp}\n"

        self.agent.agent.llm_chain.llm.callbacks = [stream_it]

        await self.agent.acall(inputs={"input": input_query})

    async def create_gen(self, query: str, chat_history: list, stream_it: AsyncCallbackHandler):
        task = asyncio.create_task(self.run_call(query, chat_history, stream_it))
        async for token in stream_it.aiter():
            yield token
        await task

    async def create_gen_openai(self, query: str, chat_history: list, stream_it: AsyncCallbackHandler):
        task = asyncio.create_task(self.run_call_no_rag(query, chat_history, stream_it))
        async for token in stream_it.aiter():
            yield token
        await task

    async def title_generation(self, text_message: str):
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful title generation assistant. Create a "
                                              "new unique title from a provided string, and the title length should "
                                              "be less than or equal to 20 characters. Please make sure it won't "
                                              "exceed more than 20 characters in any case."},
                {"role": "user", "content": text_message}
            ]
        )
        return response.choices[0].message.content

    async def response_generator(self, query: str, chat_history: list):

        ai_resp = ""
        if chat_history:
            for sender, message_text in chat_history:
                if sender.upper() == 'AI':
                    ai_resp += f"\n{message_text}\n"

        # user query
        embedding_vector = OpenAIEmbeddings().embed_query(query)

        all_content = ""
        if self.vector_db is not None:
            docs = self.vector_db.similarity_search(embedding_vector)
            all_content = '\n'.join(doc.page_content for doc in docs)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self.PREFIX},
                {"role": "user", "content": f"\n\n{all_content}\n\n{ai_resp}\n\n{query}"}
            ],
            temperature=0,
            stream=True
        )
        for chunk in response:
            # result['chat_id'] = chunk.id
            chunk_message = chunk.choices[0].delta.content  # Extract the message
            if chunk_message:
                yield chunk_message
                # result['text_message'] += chunk_message
                # yield json.dumps(chunk_message) + '\n\n\n\n'
