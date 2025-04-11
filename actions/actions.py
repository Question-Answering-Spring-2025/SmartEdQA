# actions/actions.py

import requests
import re
import json
from rasa_sdk import Action, Tracker

from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import  SlotSet, ConversationPaused
from typing import List, Dict, Any  # import List for type hints in Python 3.8

# service urls
MCQ_URL = "http://localhost:8001/mcq"
MCQS_URL = "http://localhost:8001/mcqs"
SHORT_QA_URL = "http://localhost:8002/short_qa"


class ActionRunMCQ(Action):
    def name(self) -> str:
        return "action_run_mcq"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[str, Any]) -> List[Any]:
        
        # Get the user’s message
        text = tracker.latest_message.get("text")
        if not text:
            dispatcher.utter_message(text="Please provide an MCQ to process.")
            return [SlotSet("question_type", "mcq")]

        # Check if the message contains multiple MCQs (separated by double newlines)
        mcqs = re.split(r"\n\s*\n", text.strip())
        if len(mcqs) > 1:
            # Multiple MCQs: Send to /mcqs endpoint
            payload = {"mcqs": text}
            try:
                r = requests.post(MCQS_URL, json=payload, timeout=10)
                r.raise_for_status()
            except requests.RequestException as e:
                print("Request to MCQs service failed:", e)
                dispatcher.utter_message(text="Sorry, I couldn’t reach the quiz engine.")
                return [SlotSet("question_type", "mcq")]

            if r.status_code == 200:
                response = r.json()
                answers = response.get("answers", [])
                for i, answer in enumerate(answers, 1):
                    if answer.startswith("Error:"):
                        dispatcher.utter_message(text=f"MCQ {i}: {answer}")
                    else:
                        dispatcher.utter_message(text=f"Answer to MCQ {i}: {answer}")
            else:
                print("MCQs service responded with status code:", r.status_code)
                dispatcher.utter_message(text="Sorry, I couldn’t process the MCQs.")
        else:
            # Single MCQ: Parse the input
            # First, try to split by newlines if the input uses them
            lines = text.strip().split('\n')
            if len(lines) >= 5:
                # Input is in multi-line format
                # Extract the question (with or without a question number)
                question_line = lines[0].strip()
                question_match = re.match(r"(\d+)\.\s*(.*)", question_line)
                if question_match:
                    question = question_match.group(2)
                else:
                    question = question_line

                # Extract the options (next 4 lines)
                options = "\n".join(lines[1:5]).strip()
            else:
                # Input is likely in single-line format
                # Use regex to extract question and options
                # Pattern: Question followed by A., B., C., D. options
                pattern = r"^(.*?)\s*A\.\s*(.*?)\s*B\.\s*(.*?)\s*C\.\s*(.*?)\s*D\.\s*(.*?)$"
                match = re.match(pattern, text.strip())
                if not match:
                    dispatcher.utter_message(text="Please provide a valid MCQ with a question and four options (A, B, C, D).")
                    return [SlotSet("question_type", "mcq")]

                question = match.group(1).strip()
                option_a = match.group(2).strip()
                option_b = match.group(3).strip()
                option_c = match.group(4).strip()
                option_d = match.group(5).strip()
                options = f"A. {option_a}\nB. {option_b}\nC. {option_c}\nD. {option_d}"

            # Prepare the payload for the /mcq endpoint
            payload = {
                "question": question,
                "options": options
            }

            # Send the request to the /mcq endpoint
            try:
                r = requests.post(MCQ_URL, json=payload, timeout=10)
                r.raise_for_status()
            except requests.RequestException as e:
                print("Request to MCQ service failed:", e)
                dispatcher.utter_message(text="Sorry, I couldn’t reach the quiz engine.")
                return [SlotSet("question_type", "mcq")]

            # Process the response
            if r.status_code == 200:
                response = r.json()
                answer = response.get("answer")
                if answer.startswith("Error:"):
                    dispatcher.utter_message(text=answer)
                else:
                    dispatcher.utter_message(text=f"The answer is: {answer}")
            else:
                print("MCQ service responded with status code:", r.status_code)
                dispatcher.utter_message(text="Sorry, I couldn’t process the MCQ.")

        return [SlotSet("question_type", "mcq")]

class ActionRunShortQA(Action):
    def name(self) -> str:
        return "action_run_short_qa"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[str, Any]) -> List[Any]:
        
        # Get the user’s question
        text = tracker.latest_message.get("text")
        
        # Try to parse the text as JSON to extract the question
        try:
            data = json.loads(text)
            question = data.get("question", text)  # Fallback to raw text if "question" key not found
        except json.JSONDecodeError:
            question = text  # If not JSON, use the raw text as the question
        
        payload = {"question": question}
        try:
            r = requests.post(SHORT_QA_URL, json=payload, timeout=10)
        except Exception as e:
            print("Request to Short QA service failed:", e)
            dispatcher.utter_message(text="Sorry, I couldn’t reach the short-answer engine.")
            # return []
            return [SlotSet("question_type", "short_qa")]
        
        if r.status_code == 200:
            answer = r.json().get("answer")
            print("Short QA service answer:", answer)
            dispatcher.utter_message(text=answer)
        else:
            print("Short QA service responded with status code:", r.status_code)
            dispatcher.utter_message(text="Sorry, I couldn’t reach the short-answer engine.")
        
        # return []
        return [SlotSet("question_type", "short_qa")]

class ActionHandleAmbiguousAffirm(Action):
    def name(self) -> str:
        return "action_handle_ambiguous_affirm"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[str, Any]) -> List[Any]:
        # Check the question_type slot to determine the context
        question_type = tracker.get_slot("question_type")

        if question_type == "mcq":
            dispatcher.utter_message(text="Great! Please provide your MCQ question.")
            return [SlotSet("question_type", "mcq")]
        elif question_type == "short_qa":
            dispatcher.utter_message(text="Great! Please provide your short-answer question.")
            return [SlotSet("question_type", "short_qa")]
        else:
            dispatcher.utter_message(text="I’m not sure what you’re affirming. Would you like to ask an MCQ or a short-answer question?")
            return []
        
           
class ActionEndConversation(Action):
    def name(self) -> str:
        return "action_end_conversation"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Any]:
        # End the conversation by pausing it and effectively stopping further input
        print("Ending conversation...")  # Debug log to confirm execution
        return [ConversationPaused()]
