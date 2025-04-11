from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from .mcq_engine import process_mcq, process_mcqs 

app = FastAPI()

class MCQRequest(BaseModel):
    question: str
    options: str = ""  # optional

class MCQResponse(BaseModel):
    answer: str

# Request and response models for multiple MCQs
class MCQsRequest(BaseModel):
    mcqs: str  # Multiple MCQs separated by double newlines

class MCQsResponse(BaseModel):
    answers: List[str] # instead of list(str)

@app.post("/mcq", response_model=MCQResponse)
def answer_mcq(req: MCQRequest):
    # Ensure options are provided
    if not req.options:
        return MCQResponse(answer="Error: Please provide options (A, B, C, D) for the MCQ.")
    
    # Format the MCQ text as expected by process_mcq
    mcq_text = f"{req.question}\n{req.options}"
    
    # Process the MCQ using the process_mcq function
    answer = process_mcq(mcq_text)
    return MCQResponse(answer=answer)

@app.post("/mcqs", response_model=MCQsResponse)
def answer_mcqs(req: MCQsRequest):
    # Process multiple MCQs using the process_mcqs function
    answers = process_mcqs(req.mcqs)
    return MCQsResponse(answers=answers)

