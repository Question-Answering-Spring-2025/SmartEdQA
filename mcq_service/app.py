# mcq_service/app.py
from fastapi import FastAPI
from pydantic import BaseModel
import chromadb
from .mcq_engine import load_documents, create_index, build_prompt, parse_mcq

# Clear old data
chroma_client = chromadb.EphemeralClient()
for col in chroma_client.list_collections():
    if col.name == "Biology_S3_SB":
        chroma_client.delete_collection(name="Biology_S3_SB")
                                        
app = FastAPI()

# initialize index once
docs = load_documents("./books/Biology_S3_SB_compressed.pdf")
INDEX = create_index(docs)

class MCQRequest(BaseModel):
    question: str
    options: str = ""  # optional

class MCQResponse(BaseModel):
    answer: str

@app.post("/mcq", response_model=MCQResponse)
def answer_mcq(req: MCQRequest):
    prompt = build_prompt(req.question, req.options)
    response = INDEX.as_query_engine().query(prompt)
    return MCQResponse(answer=str(response).strip())

