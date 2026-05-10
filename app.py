from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import requests
import json
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

app = FastAPI()
conversation_state = {}
# LOAD DATASET
url = "https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog.json"

response = requests.get(url)

raw_text = response.text

clean_text = re.sub(r'[\x00-\x1F\x7F]', '', raw_text)

data = json.loads(clean_text)

# CREATE SEARCHABLE TEXTS
texts = []

for item in data:

    text = f"""
    {item.get('name', '')}
    {item.get('description', '')}
    {item.get('job_levels', '')}
    {item.get('languages', '')}
    {item.get('keys', '')}
    """

    texts.append(text)

# LOAD MODEL
model = SentenceTransformer('all-MiniLM-L6-v2')

# CREATE EMBEDDINGS
embeddings = model.encode(texts)

# REQUEST MODELS
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

# HEALTH ENDPOINT
@app.get("/health")
def health():
    return {"status": "ok"}

# CHAT ENDPOINT
@app.post("/chat")
def chat(request: ChatRequest):

    global conversation_state

    query = request.messages[-1].content.lower()

    # STORE ROLE
    if "developer" in query:
        conversation_state["role"] = "developer"

    # ASK LANGUAGE
    if "language" not in conversation_state:

        if "java" in query:
            conversation_state["language"] = "java"

        elif "python" in query:
            conversation_state["language"] = "python"

        else:
            return {
                "reply": "Which programming language or technology stack are you hiring for?",
                "recommendations": [],
                "end_of_conversation": False
            }

    # ASK EXPERIENCE
    if "experience" not in conversation_state:

        if "entry" in query:
            conversation_state["experience"] = "entry-level"

        elif "mid" in query:
            conversation_state["experience"] = "mid-level"

        elif "senior" in query:
            conversation_state["experience"] = "senior"

        else:
            return {
                "reply": "What experience level are you targeting? Entry-level, mid-level, or senior?",
                "recommendations": [],
                "end_of_conversation": False
            }

    # ASK COMMUNICATION NEED
    if "communication_required" not in conversation_state:

        if "yes" in query:
            conversation_state["communication_required"] = True

        elif "no" in query:
            conversation_state["communication_required"] = False

        else:
            return {
                "reply": "Do you also want communication or behavioral assessments?",
                "recommendations": [],
                "end_of_conversation": False
            }

    # BUILD FINAL QUERY
    final_query = f"""
    {conversation_state.get('role', '')}
    {conversation_state.get('language', '')}
    {conversation_state.get('experience', '')}
    """

    if conversation_state.get("communication_required"):
        final_query += " communication behavioral"

    # CREATE QUERY EMBEDDING
    query_embedding = model.encode([final_query])

    # CALCULATE SIMILARITY
    scores = cosine_similarity(query_embedding, embeddings)[0]

    # GET TOP RESULTS
    top_indices = np.argsort(scores)[::-1][:5]

    recommendations = []

    for idx in top_indices:

        item = data[idx]

        description = item.get("description", "")

        reason = "Recommended based on the provided hiring requirements and recruiter preferences."

        category = "General Assessment"

        if conversation_state.get("language") == "java":
            category = "Technical Screening"

        if conversation_state.get("communication_required"):
            category = "Communication + Technical Screening"

        recommendations.append({
            "name": item.get("name"),
            "url": item.get("link"),
            "test_type": item.get("assessment_type", "Unknown"),
            "reason": reason,
            "recommended_stage": category,
            "description": description[:200]
        })

    workflow = [
        "1. Technical Screening",
        "2. Communication Assessment",
        "3. Behavioral Evaluation",
        "4. Final Interview"
    ]

    # CLEAR MEMORY AFTER FINAL RESPONSE
    conversation_state = {}

    return {
        "reply": "Based on the collected hiring requirements, here are the recommended SHL assessments.",
        "recommended_hiring_workflow": workflow,
        "recommendations": recommendations,
        "end_of_conversation": True
    }