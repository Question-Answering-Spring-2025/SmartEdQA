# short_engine.py
import os
import warnings
import chromadb
import openai
from typing import List, Tuple
from dotenv import load_dotenv

# LlamaIndex & Chroma
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
# from llama_index.core.vector_stores import ChromaVectorStore
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Settings

from chromadb.config import Settings as ChromaSettings
warnings.filterwarnings("ignore")

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 1) Configure LlamaIndex
# embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

Settings.llm = OpenAI(model="gpt-3.5-turbo")
Settings.embed_model = embed_model
Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)
Settings.num_output = 512
Settings.context_window = 3900

# 2) Persistent Chroma configuration
PERSIST_DIR = "./chroma_db"
COLLECTION_NAME = "Biology_S3_SB"
PDF_FILE_PATH = "../books/Biology_S3_SB_compressed.pdf"

# chroma_client = chromadb.Client(
#     ChromaSettings(
#         chroma_db_impl="duckdb+parquet",
#         persist_directory=PERSIST_DIR
#     )
# )

# Use PersistentClient instead of Client with ChromaSettings
chroma_client = chromadb.PersistentClient(path=PERSIST_DIR)
chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

def get_or_build_index() -> VectorStoreIndex:
    existing_doc_count = len(chroma_collection.get()["ids"])
    if existing_doc_count == 0:
        print("Loading PDF file...")
        # Build the index from the PDF (first time)
        documents = SimpleDirectoryReader(input_files=[PDF_FILE_PATH]).load_data()
        print(f"Loaded {len(documents)} documents from PDF.")
        
        print("Building index from documents...")
        index = VectorStoreIndex.from_documents(
            documents,
            embed_model=embed_model,
            storage_context=storage_context
        )
        print("Built new index from PDF and persisted to disk.")
    else:
        # Reuse existing Chroma data
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=embed_model
        )
        print("Loaded existing Chroma data from disk.")
    return index

# Build/reuse index at import time
index = get_or_build_index()

# Create a query engine from the index
# query_engine = index.as_query_engine()
query_engine = index.as_query_engine(similarity_top_k=3)

def build_shortqa_prompt(question: str) -> str:
    instructions = (
        "Answer the following question using relevant information from the textbook. "
        "Be concise, factual, and clear.\n\n"
    )
    few_shot_examples = (
        "Example 1:\n"
        "Q: What is the function of the heart?\n"
        "A: The heart pumps blood throughout the body, delivering oxygen and nutrients.\n\n"
        "Example 2:\n"
        "Q: What are the three types of blood vessels?\n"
        "A: Arteries, veins, and capillaries.\n\n"
    )
    question_prompt = f"Now answer the question:\nQ: {question}\nA:"
    return f"{instructions}{few_shot_examples}{question_prompt}"

def process_shortqa(question: str) -> str:
    prompt = build_shortqa_prompt(question)
    # response = index.query(prompt)
    response = query_engine.query(prompt)
    return str(response)
