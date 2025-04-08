# actions/actions.py
# the format that takes question and answer like json
#-------------------------
# { "question" : "Pollination is how flowers reproduce—what things help make it happen?"
   # "options": "A. Wind, B. Insects, C. Water, D. All of the above"}
# -------------------------------

import requests
import re
from rasa_sdk import Action, Tracker

from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import UserUtteranceReverted, SessionStarted, ActionExecuted, Restarted, SlotSet, FollowupAction, ConversationPaused
from typing import List, Dict, Any  # Import List for type hints in Python 3.8

# MCQ_URL = "http://localhost:8000/mcq"
MCQ_URL = "http://localhost:8001/mcq"

class ActionRunMCQ(Action):
    def name(self) -> str:
        return "action_run_mcq"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[str, Any]) -> List[Any]:
        
        # Get the user’s question (and options if you capture them)
        text = tracker.latest_message.get("text")
        
        payload = {"question": text, "options": ""}
        try:
            r = requests.post(MCQ_URL, json=payload, timeout=10)
        except Exception as e:
            print("Request to MCQ service failed:", e)
            dispatcher.utter_message(text="Sorry, I couldn’t reach the quiz engine.")
            return []
        
        if r.status_code == 200:
            answer = r.json().get("answer")
            print("MCQ service answer:", answer)
            dispatcher.utter_message(text=answer)
        else:
            print("MCQ service responded with status code:", r.status_code)
            dispatcher.utter_message(text="Sorry, I couldn’t reach the quiz engine.")
        
        return []

class ActionEndConversation(Action):
    def name(self) -> str:
        return "action_end_conversation"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Any]:
        # End the conversation by pausing it and effectively stopping further input
        print("Ending conversation...")  # Debug log to confirm execution
        return [ConversationPaused()]

    