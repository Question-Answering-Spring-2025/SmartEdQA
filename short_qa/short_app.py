# short_app.py
from fastapi import FastAPI
from pydantic import BaseModel
from short_engine import process_shortqa  # Updated import

app = FastAPI()

class ShortQARequest(BaseModel):
    question: str

class ShortQAResponse(BaseModel):
    answer: str

@app.post("/short_qa", response_model=ShortQAResponse)
def short_qa_handler(req: ShortQARequest):
    answer = process_shortqa(req.question)
    return ShortQAResponse(answer=answer.strip())
