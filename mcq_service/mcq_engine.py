import os
import openai
import warnings
import re
# import logging

from llama_index.core import StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from IPython.display import Markdown, display
import chromadb

from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, ServiceContext, StorageContext, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core.node_parser import SentenceSplitter
from pypdf import PdfReader

warnings.filterwarnings("ignore")

# Load environment variables and set API key for OpenAI
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Define embedding function
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")


def load_documents(file_path):
    """
    Loads documents from a given file using SimpleDirectoryReader.
    """
    return SimpleDirectoryReader(input_files=[file_path]).load_data()


def extract_text_from_pdf(file_path):
    """
    Extracts text from a PDF file.
    """
    text_data = ""
    with open(file_path, 'rb') as file:
        pdf_reader = PdfReader(file)
        for page in pdf_reader.pages:
            text_data += page.extract_text()
    return text_data


def create_index(documents, chroma_collection_name="Biology_S3_SB"):
    """
    Creates a vector index from the documents using ChromaDB.
    """
    # On startup, clear any old in-memory data:
    chroma_client = chromadb.EphemeralClient()
    # If a collection exists, delete it:
    for col in chroma_client.list_collections():
     if col.name == chroma_collection_name:
            # chroma_client.delete_collection(name="Biology_S3_SB")
            chroma_client.delete_collection(name=chroma_collection_name)
            
    chroma_collection = chroma_client.create_collection(chroma_collection_name)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection,
                                    client=chroma_client,
                                    add_kwargs={"batch_size": 80}
                                     )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Update Settings as needed
    Settings.llm = OpenAI(model="gpt-3.5-turbo")
    Settings.embed_model = embed_model
    # Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)
    Settings.node_parser = SentenceSplitter(chunk_size=90, chunk_overlap=15)
    Settings.num_output = 512
    Settings.context_window = 3900
    
    index = VectorStoreIndex.from_documents(documents, embed_model=embed_model, 
                                            storage_context=storage_context,
                                            # insert_kwargs={"batch_size": 80}
                                            insert_batch_size=80
                                            )
    
    # logging.basicConfig(level=logging.DEBUG)

# Then run your code and check the logs for batch size-related messages
    return index


def build_prompt(question, options):
    """
    Builds a prompt for the LLM using a question and its options.
    """
    instructions = (
        "Choose the correct answer (A, B, C, or D) and provide only the letter.\n\n"
        "For example, if the correct answer is B, just output:\n\n"
        "B\n\n"
        "Make sure to restate the letter of the correct answer."
    )
    prompt = (
        f"{instructions}\n\n"
        f"Question: {question}\n\n"
        f"Options:\n{options}\n\n"
    )
    return prompt


def parse_mcq(mcq_block):
    """
    Parses an MCQ block to extract the question number, question text, and options.
    """
    lines = mcq_block.strip().split('\n')
    question_line = lines[0]
    question_match = re.match(r"(\d+)\.\s*(.*)", question_line)
    q_number = question_match.group(1)
    question = question_match.group(2)
    options = "\n".join(lines[1:])
    return q_number, question, options


def process_mcqs(mcq_text, index, output_file_path):
    """
    Processes multiple MCQs from a text block, queries the LLM, and writes the responses.
    """
    mcqs = re.split(r"\n\s*\n", mcq_text.strip())
    responses = []
    
    with open(output_file_path, "w", encoding="utf-8") as outfile:
        for mcq in mcqs:
            q_number, question, options = parse_mcq(mcq)
            full_prompt = build_prompt(question, options)
    
            # Query the index using your LLM
            query_engine = index.as_query_engine()
            response = query_engine.query(full_prompt)
            raw_answer = str(response).strip()
    
            # Extract the letter (A-D) from the response
            match = re.match(r"\s*([A-D])[\.\s\-:)]*", raw_answer, re.IGNORECASE)
            answer_letter = match.group(1).upper() if match else raw_answer
    
            output_line = f"{q_number}. {answer_letter}"
            outfile.write(output_line + "\n\n")
            responses.append(output_line)
    
    return responses
