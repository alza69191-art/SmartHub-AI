import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from groq import Groq

app = FastAPI(title="SmartHub AI API", version="1.0.0")

# GitHub Pages is a separate origin. Restrict this list to your published
# frontend domain after deployment by setting FRONTEND_ORIGIN on Render.
frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in frontend_origin.split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    history: list[dict] = Field(default_factory=list)

@app.get("/")
def root():
    return {"service": "SmartHub AI API", "status": "online"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/chat")
def chat(payload: ChatRequest):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured on the server.")

    messages = [{
        "role": "system",
        "content": "You are SmartHub AI, a helpful, accurate assistant. Reply in the user's language. Be concise, structured, and honest about uncertainty."
    }]

    # Keep only valid recent user/assistant messages and limit context size.
    for item in payload.history[-10:]:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content[:4000]})

    messages.append({"role": "user", "content": payload.message})

    try:
        client = Groq(api_key=api_key)
        result = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=0.7,
            max_tokens=1200,
        )
        return {"reply": result.choices[0].message.content or ""}
    except Exception:
        raise HTTPException(status_code=502, detail="Groq request failed. Check the server logs and Groq API status.")
