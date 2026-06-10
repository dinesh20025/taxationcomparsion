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
        yield " "                                  # 🚀 turant first byte (Azure proxy zinda rakho)  
        try:  
            for chunk in core.ask_stream(q.question):  
                yield chunk  
        except GeneratorExit:  
            return                                 # 🛑 user stop kare to band  
  
    return StreamingResponse(  
        generate(),  
        media_type="text/plain",  
        headers={  
            "X-Accel-Buffering": "no",             # 🔑 buffering off (streaming smooth)  
            "Cache-Control": "no-cache",  
        },  
    )  
  
  
# health check (Azure ke liye)  
@app.get("/health")  
def health():  
    return {"status": "ok", "sections": len(core.SECTIONS)}
