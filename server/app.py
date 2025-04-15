from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from deep_researcher import DeepResearcher
from deep_researcher.sse_manager import SSEManager
from pydantic import BaseModel
import os
import traceback
import uuid
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class ResearchRequest(BaseModel):
    query: str
    max_iterations: int = 3
    max_time_minutes: int = 10

@app.post("/api/research")
async def start_research(request: ResearchRequest):
    """启动研究任务的POST端点"""
    client_id = str(uuid.uuid4())
    researcher = DeepResearcher(
        max_iterations=request.max_iterations,
        max_time_minutes=request.max_time_minutes,
        verbose=True,
        tracing=False,
        client_id=client_id
    )
    asyncio.create_task(researcher.run(query=request.query,client_id=client_id))
    
    return JSONResponse({
        "status": "started",
        "client_id": client_id,
        "sse_url": f"/sse/{client_id}"
    })

@app.get("/")
async def get_index():
    try:
        print(f"当前工作目录: {os.getcwd()}")
        
        frontend_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
        )
        print(f"尝试加载前端文件路径: {frontend_path}")
        
        if not os.path.exists(frontend_path):
            raise FileNotFoundError(f"前端文件未找到: {frontend_path}")
            
        if not os.access(frontend_path, os.R_OK):
            raise PermissionError(f"无读取权限: {frontend_path}")
            
        return FileResponse(frontend_path)
        
    except Exception as e:
        print("="*50)
        print("发生错误:")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print("堆栈跟踪:")
        traceback.print_exc()
        print("="*50)
        raise

@app.get("/sse/{client_id}")
async def sse_endpoint(request: Request, client_id: str):
    async def event_stream():
        queue = SSEManager.subscribe(client_id)
        try:
            while True:
                event = await queue.get()
                if event is None:  # 添加检查
                    break
                # 修改消息格式
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            SSEManager.unsubscribe(client_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )