#!/usr/bin/env python3
"""
NEXUS Web Interface — FastAPI Backend
Expõe o agente NEXUS via API REST para uso em navegador
"""

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
from pathlib import Path

# Import do NEXUS
import sys
sys.path.insert(0, str(Path(__file__).parent))
from NEXUS_COMPLETE import NexusAgent

# Setup
app = FastAPI(title="NEXUS Web", description="AGI Local via Web")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instância global do agente
agent: NexusAgent = None
active_connections: dict = {}

# ═════════════════════════════════════════════════════════════
# LIFECYCLE
# ═════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup():
    global agent
    logger.info("🚀 Inicializando NEXUS...")
    agent = NexusAgent()
    await agent.initialize()
    logger.info("✅ NEXUS pronto!")

# ═════════════════════════════════════════════════════════════
# REST API
# ═════════════════════════════════════════════════════════════

@app.get("/api/status")
async def status():
    """Status completo do agente"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    import time
    uptime = time.time() - agent._start_time
    h, m = int(uptime//3600), int((uptime%3600)//60)
    
    from NEXUS_COMPLETE import HARDWARE, PROFILE
    return {
        "status": "ready",
        "profile": PROFILE,
        "hardware": HARDWARE,
        "llm": {
            "available": agent.llm.available,
            "provider": agent.llm.provider,
            "model": agent.llm.model,
        },
        "kb_entries": agent.kb.count(),
        "reflections": agent.auto_improve.metrics["reflections"],
        "score": agent.auto_improve.metrics["score"],
        "uptime": f"{h}h{m}m",
        "commands_executed": len(agent.tools.history),
        "tasks_scheduled": len(agent.scheduler.tasks),
        "circuit_breaker": agent.circuit_breaker.state,
    }

@app.post("/api/process")
async def process(data: dict):
    """Processa mensagem do usuário"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    user_input = data.get("message", "").strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="Message required")
    
    try:
        response = await agent.process(user_input)
        return {
            "success": True,
            "response": response,
            "kb_entries": agent.kb.count(),
            "score": agent.auto_improve.metrics["score"],
        }
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return {
            "success": False,
            "error": str(e),
        }

@app.get("/api/kb")
async def get_kb():
    """Lista entradas da base de conhecimento"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    entries = agent.kb.get_recent(20)
    return {
        "total": agent.kb.count(),
        "recent": entries,
    }

@app.get("/api/learning")
async def get_learning():
    """Retorna sumário de auto-melhoria"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return agent.auto_improve.get_learning_summary()

@app.post("/api/clear-memory")
async def clear_memory():
    """Limpa memória da sessão"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    agent.memory.turns.clear()
    return {"success": True, "message": "Memory cleared"}

@app.get("/api/plugins")
async def get_plugins():
    """Lista plugins disponíveis"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return {"plugins": agent.plugins.list_plugins()}

@app.post("/api/plugin")
async def execute_plugin(data: dict):
    """Executa um plugin"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    plugin_name = data.get("name", "").strip()
    if not plugin_name:
        raise HTTPException(status_code=400, detail="Plugin name required")
    
    try:
        result = await agent.plugins.execute(plugin_name)
        return result
    except Exception as e:
        logger.error(f"❌ Plugin error: {e}")
        return {
            "success": False,
            "error": str(e),
        }

# ═════════════════════════════════════════════════════════════
# WEBSOCKET (Real-time streaming)
# ═════════════════════════════════════════════════════════════

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para chat em tempo real"""
    await websocket.accept()
    client_id = id(websocket)
    active_connections[client_id] = websocket
    
    logger.info(f"✅ Client {client_id} connected")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data) if isinstance(data, str) else data
            user_input = message.get("message", "").strip()
            
            if not user_input:
                await websocket.send_json({"error": "Message required"})
                continue
            
            # Enviar status
            await websocket.send_json({
                "type": "status",
                "message": "🧠 Processando...",
            })
            
            try:
                # Processar
                response = await agent.process(user_input)
                
                # Enviar resposta
                await websocket.send_json({
                    "type": "response",
                    "message": response,
                    "kb_entries": agent.kb.count(),
                    "score": agent.auto_improve.metrics["score"],
                })
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })
    
    except Exception as e:
        logger.info(f"❌ Client {client_id} disconnected: {e}")
    finally:
        del active_connections[client_id]

# ═════════════════════════════════════════════════════════════
# STATIC FILES
# ═════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """Serve index.html"""
    return FileResponse("static/index.html", media_type="text/html")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico", status_code=204)

# Servir arquivos estáticos
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    logger.warning("⚠️ Static directory not found")

# ═════════════════════════════════════════════════════════════
# CLI
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print("""
    \033[36m╔═══════════════════════════════════════════════════════╗
    ║  🌐 NEXUS Web Interface                               ║
    ║                                                       ║
    ║  🚀 Servidor iniciando em:                            ║
    ║     http://localhost:8000                             ║
    ║                                                       ║
    ║  📡 API:      /api/*                                  ║
    ║  💬 WebSocket: ws://localhost:8000/ws/chat            ║
    ║  🎨 Frontend: /                                       ║
    ╚═══════════════════════════════════════════════════════╝\033[0m
    """)
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
