import os
import openai
import warnings
import re
import chromadb

from typing import Tuple, List  

from llama_index.core import StorageContext, VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core.node_parser import SentenceSplitter
from pypdf import PdfReader

from dotenv import load_dotenv

warnings.filterwarnings("ignore")

# Load environment variables and set API key for OpenAI
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Define embedding function
# embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

# Persistent Chroma configuration
PERSIST_DIR = "./chroma_db_mcq"
COLLECTION_NAME = "Biology_S3_SB_MCQ"
PDF_FILE_PATH = "./books/Biology_S3_SB_compressed.pdf"

# Use PersistentClient for Chroma
chroma_client = chromadb.PersistentClient(path=PERSIST_DIR)
chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Configure LlamaIndex Settings
Settings.llm = OpenAI(model="gpt-3.5-turbo")
Settings.embed_model = embed_model
# Settings.node_parser = SentenceSplitter(chunk_size=90, chunk_overlap=15)
Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)
Settings.num_output = 512
Settings.context_window = 3900

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

def get_or_build_index() -> VectorStoreIndex:
    """
    Builds or loads a vector index from the Chroma persistent storage.
    """
    existing_doc_count = len(chroma_collection.get()["ids"])
    if existing_doc_count == 0:
        print("Loading PDF file...")
        documents = load_documents(PDF_FILE_PATH)
        print(f"Loaded {len(documents)} documents from PDF.")
        print("Building index from documents...")
        index = VectorStoreIndex.from_documents(
            documents,
            embed_model=embed_model,
            storage_context=storage_context,
            insert_batch_size=80
        )
        print("Built new index from PDF and persisted to disk.")
    else:
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=embed_model
        )
        print("Loaded existing Chroma data from disk.")
    return index

# Build/reuse index at import time
index = get_or_build_index()

# Create the query engine with similarity_top_k=3
query_engine = index.as_query_engine(similarity_top_k=3)

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

def parse_mcq(mcq_text: str) -> Tuple[str, str, str]:
    """
    Parses an MCQ text to extract the question number (if present), question text, and options.
    
    Args:
        mcq_text (str): The MCQ text, e.g.:
            "What is the primary function of the heart?\nA. To digest food\nB. To pump blood\nC. To filter waste\nD. To produce hormones"
    
    Returns:
        tuple: (q_number, question, options) where q_number is an empty string if not present
    """
    lines = mcq_text.strip().split('\n')
    question_line = lines[0].strip()
    
    # Check if the question line starts with a number (e.g., "1.")
    question_match = re.match(r"(\d+)\.\s*(.*)", question_line)
    if question_match:
        q_number = question_match.group(1)
        question = question_match.group(2)
    else:
        q_number = ""
        question = question_line
    
    # Ensure there are options
    if len(lines) < 5:
        raise ValueError("MCQ format invalid: Must have a question and four options (A, B, C, D)")
    
    options = "\n".join(lines[1:5]).strip()
    return q_number, question, options

def process_mcq(mcq_text: str) -> str:
    """
    Processes a single MCQ and returns the answer as a string (e.g., 'B').
    
    Args:
        mcq_text (str): The MCQ text, e.g.:
            "What is the primary function of the heart?\nA. To digest food\nB. To pump blood\nC. To filter waste\nD. To produce hormones"
    
    Returns:
        str: The answer letter (e.g., 'B')
    """
    # Parse the MCQ
    q_number, question, options = parse_mcq(mcq_text)
    
    # Build the prompt
    prompt = build_prompt(question, options)
    
    # Query the index using the query engine
    response = query_engine.query(prompt)
    raw_answer = str(response).strip()
    
    # Extract the letter (A-D) from the response
    match = re.match(r"\s*([A-D])[\.\s\-:)]*", raw_answer, re.IGNORECASE)
    answer_letter = match.group(1).upper() if match else raw_answer
    
    return answer_letter

def process_mcqs(mcq_text: str) -> List[str]:
    """
    Processes multiple MCQs from a text block and returns the responses as a list of strings.
    
    Args:
        mcq_text (str): The MCQ text block, e.g.:
            "What is the primary function of the heart?\nA. To digest food\nB. To pump blood\nC. To filter waste\nD. To produce hormones\n\n1. What are the three types of blood vessels?\nA. Arteries, veins, and capillaries\nB. Red, white, and blue\nC. Large, medium, and small\nD. Aorta, vena cava, and pulmonary"
    
    Returns:
        list[str]: A list of responses, e.g., ['B', '1. A']
    """
    mcqs = re.split(r"\n\s*\n", mcq_text.strip())
    responses = []
    
    for mcq in mcqs:
        q_number, question, options = parse_mcq(mcq)
        prompt = build_prompt(question, options)
        response = query_engine.query(prompt)
        raw_answer = str(response).strip()
        match = re.match(r"\s*([A-D])[\.\s\-:)]*", raw_answer, re.IGNORECASE)
        answer_letter = match.group(1).upper() if match else raw_answer
        output_line = f"{q_number}. {answer_letter}" if q_number else f"{answer_letter}"
        responses.append(output_line)
    
    return responses
