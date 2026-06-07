from fastapi import FastAPI, Request  
from fastapi.responses import StreamingResponse, FileResponse  
from fastapi.staticfiles import StaticFiles  
from pydantic import BaseModel  
import chatbot_core as core  
  
app = FastAPI(title="Income Tax AI")  
  
class Query(BaseModel):  
    question: str  
  
@app.get("/")  
def home():  
    return FileResponse("static/index.html")  
  
@app.post("/api/chat")  
def chat(q: Query):  
    def generate():  
        for chunk in core.ask_stream(q.question):  
            yield chunk  
    return StreamingResponse(generate(), media_type="text/plain")  
  
# health check (Azure ke liye)  
@app.get("/health")  
def health():  
    return {"status": "ok", "sections": len(core.SECTIONS)}
