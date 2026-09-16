from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.search_service import search_documents


app = FastAPI(
    title="Internal Chatbot with RBAC",
    description="RAG-based internal chatbot with Role-Based Access Control"
)
security = HTTPBasic()

# Dummy user database
users_db: Dict[str, Dict[str, str]] = {
    "Tony": {"password": "password123", "role": "engineering"},
    "Bruce": {"password": "securepass", "role": "marketing"},
    "Sam": {"password": "financepass", "role": "finance"},
    "Peter": {"password": "pete123", "role": "engineering"},
    "Sid": {"password": "sidpass123", "role": "marketing"},
    "Natasha": {"password": "hrpass123", "role": "hr"}
}


# Authentication dependency
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    user = users_db.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": username, "role": user["role"]}


# Login endpoint
@app.get("/login")
def login(user=Depends(authenticate)):
    return {"message": f"Welcome {user['username']}!", "role": user["role"]}


# Protected test endpoint
@app.get("/test")
def test(user=Depends(authenticate)):
    return {"message": f"Hello {user['username']}! You can now chat.", "role": user["role"]}


# Protected chat endpoint
@app.post("/chat", response_model=ChatResponse)
def query(
    user=Depends(authenticate),
    request: Optional[ChatRequest] = None,
    message: Optional[str] = None
):
    """
    Role-Based Access Control (RBAC) Chat Endpoint.
    Searches documents in resources/data/ strictly permitted for the authenticated user's role.
    """
    query_text = ""
    if request and request.message:
        query_text = request.message
    elif message:
        query_text = message
    else:
        query_text = "Hello"

    role = user["role"]
    response = search_documents(query=query_text, role=role)
    return response