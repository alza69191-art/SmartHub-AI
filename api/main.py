import logging
import os
import base64
import threading
import re
import uuid
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row
from jose import jwt, JWTError
from fastapi import Depends
from starlette.concurrency import run_in_threadpool
from gradio_client import Client
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from groq import Groq
from database import initialize_database, database_is_ready

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smarthub")

app = FastAPI(title="SmartHub AI API", version="1.1.0")

frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in frontend_origin.split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

@app.on_event("startup")
def startup():
    try:
        initialize_database()
    except Exception:
        logger.exception("PostgreSQL initialization failed")

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    history: list[dict] = Field(default_factory=list)

def build_messages(payload):
    messages = [{
        "role": "system",
        "content": "You are SmartHub AI, a helpful, accurate assistant. Reply in the user's language. Be concise, structured, and honest about uncertainty."
    }]
    for item in payload.history[-10:]:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content[:4000]})
    messages.append({"role": "user", "content": payload.message})
    return messages

def ask_groq(messages):
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    result = Groq(api_key=key).chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        temperature=0.7,
        max_tokens=1200,
    )
    return result.choices[0].message.content or ""

def ask_gemini(messages):
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    contents = []
    system_text = ""
    for item in messages:
        if item["role"] == "system":
            system_text = item["content"]
        else:
            contents.append({
                "role": "model" if item["role"] == "assistant" else "user",
                "parts": [{"text": item["content"]}]
            })
    response = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        params={"key": key},
        json={
            "systemInstruction": {"parts": [{"text": system_text}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1200},
        },
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    return "".join(
        part.get("text", "")
        for part in data["candidates"][0]["content"]["parts"]
        if "text" in part
    )

def ask_huggingface(messages):
    key = os.getenv("HF_TOKEN")
    if not key:
        raise RuntimeError("HF_TOKEN is not configured")
    response = requests.post(
        "https://router.huggingface.co/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": "openai/gpt-oss-120b:fastest",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1200,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"].get("content") or ""

@app.get("/")
def root():
    return {"service": "SmartHub AI API", "status": "online"}

@app.get("/health")
def health():
    return {
        "status": "ok",
        "database": "connected" if database_is_ready() else "unavailable",
        "providers": {
            "groq": bool(os.getenv("GROQ_API_KEY")),
            "gemini": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "huggingface": bool(os.getenv("HF_TOKEN")),
        },
    }

@app.post("/api/chat")
def chat(payload: ChatRequest):
    messages = build_messages(payload)
    providers = [
        ("Groq", ask_groq),
        ("Google Gemini", ask_gemini),
        ("Hugging Face", ask_huggingface),
    ]
    errors = []
    for name, provider in providers:
        try:
            reply = provider(messages)
            if reply.strip():
                logger.info("Chat request completed with %s", name)
                return {"reply": reply, "provider": name}
            raise RuntimeError("Provider returned an empty response")
        except Exception as exc:
            # Log provider errors server-side without exposing API keys to the browser.
            logger.exception("%s request failed", name)
            errors.append(f"{name}: {type(exc).__name__}")
    raise HTTPException(
        status_code=502,
        detail="All configured AI providers failed. Check Render logs and verify API keys, model access, and quotas. " + "; ".join(errors),
    )


# Qwen Image 2.1 generation through the official public Hugging Face Space.
_qwen_client = None
_qwen_lock = threading.Lock()

class ImageGenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    enhance_prompt: bool = True
    quality: str = Field(default="speed", pattern="^(speed|quality)$")
    custom_size: bool = False
    width: int = Field(default=1024, ge=256, le=2688)
    height: int = Field(default=1024, ge=256, le=2688)
    negative_prompt: str = Field(default="", max_length=1500)
    seed: int = Field(default=0, ge=0, le=2147483647)

def get_qwen_client():
    global _qwen_client
    if _qwen_client is None:
        token = os.getenv("HF_TOKEN", "").strip() or None
        _qwen_client = Client(
            "Qwen/Qwen-Image-2.1",
            token=token,
            verbose=False,
        )
    return _qwen_client

def qwen_image_to_data_url(result):
    # Gradio Image outputs are normally downloaded to a local filepath.
    if isinstance(result, (tuple, list)) and result:
        result = result[0]
    if isinstance(result, dict):
        result = result.get("path") or result.get("url")
    if not isinstance(result, str):
        raise RuntimeError("Qwen returned an unsupported image result")
    if result.startswith("http://") or result.startswith("https://"):
        image_response = requests.get(result, timeout=90)
        image_response.raise_for_status()
        raw = image_response.content
    else:
        with open(result, "rb") as image_file:
            raw = image_file.read()
    if not raw:
        raise RuntimeError("Qwen returned an empty image")
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")

def generate_qwen_image(payload):
    # The Space uses a two-stage flow: prepare_request creates request_state,
    # then generate_request consumes that state to run the GPU generation.
    with _qwen_lock:
        client = get_qwen_client()
        prepared = client.predict(
            input_images=None,
            original_prompt=payload.prompt,
            enable_extend=payload.enhance_prompt,
            custom_size=payload.custom_size,
            quality=payload.quality,
            seed=payload.seed,
            randomize_seed=True,
            api_name="/prepare_request",
        )
        if not isinstance(prepared, (tuple, list)) or len(prepared) < 4:
            raise RuntimeError("Unexpected response from Qwen prepare stage")
        request_state = prepared[3]
        actual_seed = prepared[1]
        image_result = client.predict(
            request_state=request_state,
            original_prompt=payload.prompt,
            enable_extend=payload.enhance_prompt,
            custom_size=payload.custom_size,
            log_dir="./generation_logs_paper_case",
            seed=actual_seed,
            height=payload.height,
            width=payload.width,
            negative_prompt=payload.negative_prompt or " ",
            api_name="/generate_request",
        )
        return {
            "image": qwen_image_to_data_url(image_result),
            "seed": actual_seed,
            "model": "Qwen Image 2.1",
            "enhanced_prompt": prepared[2] or "",
        }

@app.post("/api/images/generate")
async def generate_image(payload: ImageGenerateRequest, user=Depends(current_user)):
    try:
        result = await run_in_threadpool(generate_qwen_image, payload)
        logger.info("Qwen image generated for user %s", user["id"])
        return result
    except Exception as exc:
        logger.exception("Qwen Image 2.1 generation failed")
        raise HTTPException(
            status_code=502,
            detail="تعذر توليد الصورة حالياً. تحقق من حالة Hugging Face Space وسجلات Render.",
        )

# Authentication and support API
bearer = HTTPBearer(auto_error=False)
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"

class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=2, max_length=80)
    admin_setup_key: str = Field(default="", max_length=200)

class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)

class TicketRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=10, max_length=5000)

class ReplyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)

def db_connect():
    url = os.getenv("DATABASE_URL", "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if not url:
        raise HTTPException(status_code=503, detail="قاعدة البيانات غير مهيأة")
    return psycopg.connect(url, connect_timeout=10, row_factory=dict_row)

def ensure_auth_config():
    if len(JWT_SECRET) < 32:
        raise HTTPException(status_code=503, detail="أضف JWT_SECRET بطول 32 حرفاً على الأقل في Render")

def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + "$" + digest.hex()

def password_matches(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        candidate = password_hash(password, bytes.fromhex(salt_hex)).split("$", 1)[1]
        return hmac.compare_digest(candidate, digest_hex)
    except Exception:
        return False

def admin_email(email):
    allowed = {x.strip().lower() for x in os.getenv("ADMIN_EMAILS", "").split(",") if x.strip()}
    return email.lower() in allowed

def make_token(profile):
    ensure_auth_config()
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(profile["id"]), "iat": now,
                       "exp": now + timedelta(hours=24)}, JWT_SECRET, algorithm="HS256")

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    ensure_auth_config()
    if not credentials:
        raise HTTPException(status_code=401, detail="سجّل الدخول أولاً")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user_id = str(uuid.UUID(payload.get("sub", "")))
    except Exception:
        raise HTTPException(status_code=401, detail="جلسة الدخول غير صالحة")
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id,email,display_name,role,created_at FROM profiles WHERE id=%s", (user_id,))
            user = cur.fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="الحساب غير موجود")
    return user

def require_admin(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="هذه العملية للإدارة فقط")
    return user

@app.post("/api/auth/register")
def register(payload: RegisterRequest):
    ensure_auth_config()
    email = payload.email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="البريد الإلكتروني غير صالح")
    user_id = uuid.uuid4()
    setup_key = os.getenv("ADMIN_SETUP_KEY", "")
    is_admin = bool(setup_key) and admin_email(email) and hmac.compare_digest(payload.admin_setup_key, setup_key)
    role = "admin" if is_admin else "user"
    try:
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO profiles (id,auth_subject,email,display_name,role,password_hash)
                               VALUES (%s,%s,%s,%s,%s,%s)
                               RETURNING id,email,display_name,role,created_at""",
                            (str(user_id),str(user_id),email,payload.display_name.strip(),role,password_hash(payload.password)))
                profile = cur.fetchone()
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="هذا البريد مسجل مسبقاً")
    return {"token": make_token(profile), "user": profile}

@app.post("/api/auth/login")
def login(payload: LoginRequest):
    ensure_auth_config()
    email = payload.email.strip().lower()
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id,email,display_name,role,password_hash,created_at FROM profiles WHERE email=%s", (email,))
            profile = cur.fetchone()
            if not profile or not profile.get("password_hash") or not password_matches(payload.password, profile["password_hash"]):
                raise HTTPException(status_code=401, detail="البريد أو كلمة المرور غير صحيحة")
            role = "admin" if (profile["role"] == "admin" and admin_email(email)) else "user"
            cur.execute("UPDATE profiles SET role=%s WHERE id=%s RETURNING id,email,display_name,role,created_at", (role,str(profile["id"])))
            profile = cur.fetchone()
    return {"token": make_token(profile), "user": profile}

@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return {"user": user}

@app.post("/api/support/tickets")
def create_ticket(payload: TicketRequest, user=Depends(current_user)):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO support_tickets (user_id,subject,message) VALUES (%s,%s,%s) RETURNING id,subject,message,status,priority,created_at,updated_at",
                        (str(user["id"]),payload.subject.strip(),payload.message.strip()))
            return cur.fetchone()

@app.get("/api/support/tickets")
def list_tickets(user=Depends(current_user)):
    with db_connect() as conn:
        with conn.cursor() as cur:
            if user["role"] == "admin":
                cur.execute("""SELECT t.id,t.user_id,p.email,t.subject,t.message,t.status,t.priority,t.created_at,t.updated_at
                               FROM support_tickets t JOIN profiles p ON p.id=t.user_id ORDER BY t.updated_at DESC LIMIT 200""")
            else:
                cur.execute("""SELECT id,user_id,subject,message,status,priority,created_at,updated_at
                               FROM support_tickets WHERE user_id=%s ORDER BY updated_at DESC""",(str(user["id"]),))
            return {"tickets":cur.fetchall()}

@app.get("/api/support/tickets/{ticket_id}/replies")
def list_replies(ticket_id: int, user=Depends(current_user)):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM support_tickets WHERE id=%s",(ticket_id,))
            ticket=cur.fetchone()
            if not ticket: raise HTTPException(status_code=404,detail="التذكرة غير موجودة")
            if user["role"]!="admin" and str(ticket["user_id"])!=str(user["id"]):
                raise HTTPException(status_code=403,detail="لا يمكنك الوصول إلى هذه التذكرة")
            cur.execute("""SELECT r.id,r.ticket_id,r.sender_role,r.message,r.created_at,p.display_name
                           FROM support_replies r LEFT JOIN profiles p ON p.id=r.sender_user_id
                           WHERE r.ticket_id=%s ORDER BY r.created_at""",(ticket_id,))
            return {"replies":cur.fetchall()}

@app.post("/api/support/tickets/{ticket_id}/replies")
def add_reply(ticket_id: int,payload: ReplyRequest,user=Depends(current_user)):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM support_tickets WHERE id=%s FOR UPDATE",(ticket_id,))
            ticket=cur.fetchone()
            if not ticket: raise HTTPException(status_code=404,detail="التذكرة غير موجودة")
            if user["role"]!="admin" and str(ticket["user_id"])!=str(user["id"]):
                raise HTTPException(status_code=403,detail="لا يمكنك الرد على هذه التذكرة")
            role="admin" if user["role"]=="admin" else "user"
            cur.execute("""INSERT INTO support_replies (ticket_id,sender_user_id,sender_role,message)
                           VALUES (%s,%s,%s,%s) RETURNING id,ticket_id,sender_role,message,created_at""",
                        (ticket_id,str(user["id"]),role,payload.message.strip()))
            reply=cur.fetchone()
            cur.execute("UPDATE support_tickets SET status=%s,updated_at=NOW() WHERE id=%s",
                        ("answered" if role=="admin" else "in_progress",ticket_id))
            return reply

@app.patch("/api/support/tickets/{ticket_id}/status")
def update_ticket_status(ticket_id: int,status: str,user=Depends(require_admin)):
    if status not in {"open","in_progress","answered","closed"}:
        raise HTTPException(status_code=422,detail="حالة التذكرة غير صالحة")
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE support_tickets SET status=%s,updated_at=NOW() WHERE id=%s RETURNING id,status",(status,ticket_id))
            result=cur.fetchone()
            if not result: raise HTTPException(status_code=404,detail="التذكرة غير موجودة")
            return result
