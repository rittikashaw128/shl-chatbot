from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import requests
import json
import re
conversation_memory = {}
STAGES = {
    "START": "start",
    "EXPERIENCE": "experience",
    "LOCATION": "location",
    "FINAL": "final"
}
def initialize_session(session_id):

    if session_id not in conversation_memory:

        conversation_memory[session_id] = {
            "stage": STAGES["START"],
            "role_interest": None,
            "experience": None,
            "location": None,
            "recommendations": []
        }

app = FastAPI()

conversation_state = {}

# LOAD DATASET
url = "https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog"

try:
    response = requests.get(url, timeout=10)

    raw_text = response.text

    clean_text = re.sub(r'[\x00-\x1F\x7F]', '', raw_text)

    data = json.loads(clean_text)

except Exception as e:
    print("DATA LOAD ERROR:", e)
    data = []

# CREATE SEARCHABLE TEXTS
texts = []

for item in data:
    text = f"""
    name: {item.get('name', '')}
    description: {item.get('description', '')}
    category: {item.get('category', '')}
    """
    texts.append(text.lower())


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str
    messages: List[Message]


@app.get("/")
def home():
    return {"message": "SHL Chatbot Running Successfully"}


@app.post("/chat")
def chat(req: ChatRequest):

    session_id = req.session_id

    initialize_session(session_id)

    state = conversation_memory[session_id]

    latest_message = req.messages[-1].content.lower()

    # START
    if state["stage"] == STAGES["START"]:

        state["role_interest"] = latest_message
        state["stage"] = STAGES["EXPERIENCE"]

        return {
            "response": "What experience level are you looking for?",
            "stage": state["stage"]
        }

    # EXPERIENCE
    elif state["stage"] == STAGES["EXPERIENCE"]:

        state["experience"] = latest_message
        state["stage"] = STAGES["LOCATION"]

        return {
            "response": "Do you prefer remote or onsite opportunities?",
            "stage": state["stage"]
        }

    # LOCATION
    elif state["stage"] == STAGES["LOCATION"]:

        state["location"] = latest_message

        recommendations = search_recommendations(
            state["role_interest"]
        )

        state["recommendations"] = recommendations
        state["stage"] = STAGES["FINAL"]

        return {
            "response": "Here are your top recommendations.",
            "recommendations": recommendations,
            "conversation_complete": True
        }


def search_recommendations(query):

    results = []

    for item in data:

        title = item.get("name", "").lower()

        if query.lower() in title:

            results.append({
                "name": item.get("name"),
                "category": item.get("category"),
                "description": item.get("description")
            })

    return results[:5]