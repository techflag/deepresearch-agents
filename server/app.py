from fastapi import FastAPI, WebSocket
from deep_researcher import DeepResearcher

app = FastAPI()
@app.get("/")
async def get_index():
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    return FileResponse(frontend_path)
    
@app.websocket("/ws/research")
async def research_websocket(websocket: WebSocket):
    await websocket.accept()
    
    try:
        # 接收研究参数
        data = await websocket.receive_json()
        
        # 初始化研究者
        researcher = DeepResearcher(
            max_iterations=3,
            max_time_minutes=10,
            verbose=True,
            websocket=websocket
        )
        
        # 执行研究
        report = await researcher.run(
            query=data["query"]
        )
        
        # 发送完成信号
        await websocket.send_json({
            "type": "complete",
            "report": report
        })
        
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })