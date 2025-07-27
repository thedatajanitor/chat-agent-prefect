"""
Chat Agent Backend with Prefect Pause/Resume
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from typing import Dict, Optional
from datetime import datetime
import uuid
import os
from pydantic import BaseModel

from prefect.client import get_client
import json

# Import the flow from the flows module
from app.flows.chat_flow import chat_pause_resume_flow

# Store WebSocket connections (must be here for flow to access)
websocket_manager: Dict[str, WebSocket] = {}
# Store flow run IDs
flow_runs: Dict[str, str] = {}  # session_id -> flow_run_id
# Store flow tasks
flow_tasks: Dict[str, asyncio.Task] = {}  # session_id -> task

# Set Prefect API URL if provided
if os.getenv("PREFECT_API_URL"):
    import prefect
    prefect.settings.PREFECT_API_URL = os.getenv("PREFECT_API_URL")


class WebSocketUpdate(BaseModel):
    """Model for internal WebSocket updates"""
    session_id: str
    type: str
    data: dict


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Chat Agent with Prefect Pause/Resume...")
    yield
    print("Shutting down...")


app = FastAPI(
    title="Chat Agent with Prefect Pause/Resume",
    version="5.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    prefect_connected = False
    try:
        async with get_client() as client:
            await client.read_flow_runs(limit=1)
            prefect_connected = True
    except:
        pass
    
    return {
        "status": "healthy",
        "active_sessions": len(websocket_manager),
        "active_flows": len(flow_runs),
        "prefect_connected": prefect_connected
    }


@app.post("/api/chat/start")
async def start_chat_session():
    """Start a new chat session"""
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    print(f"\n=== NEW SESSION: {session_id} ===\n")
    return {
        "session_id": session_id,
        "created_at": datetime.now().isoformat()
    }


@app.post("/api/internal/websocket-update")
async def internal_websocket_update(update: WebSocketUpdate):
    """Internal endpoint for flows to send WebSocket updates"""
    if update.session_id in websocket_manager:
        await send_to_websocket(update.session_id, update.type, update.data)
        return {"status": "sent"}
    return {"status": "no_connection"}


async def send_to_websocket(session_id: str, msg_type: str, content: dict):
    """Helper to send messages to WebSocket if connected"""
    if session_id in websocket_manager:
        try:
            await websocket_manager[session_id].send_json({
                "type": msg_type,
                **content,
                "timestamp": datetime.now().isoformat()
            })
            print(f"[WS] Sent {msg_type} to {session_id}")
        except Exception as e:
            print(f"[WS] Error sending to {session_id}: {e}")


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    websocket_manager[session_id] = websocket
    print(f"\n=== WEBSOCKET CONNECTED: {session_id} ===\n")
    
    try:
        while True:
            data = await websocket.receive_json()
            print(f"\n=== RECEIVED: {json.dumps(data, indent=2)} ===\n")
            
            if data.get("type") == "user_message":
                message = data.get("message", "")
                
                if session_id not in flow_runs:
                    # First message - start new flow
                    print(f"[WS] Starting new Prefect flow for {session_id}")
                    print(f"[WS] Initial message: {message}")
                    
                    try:
                        # Create and start the flow, passing the flow_runs dict
                        flow_task = asyncio.create_task(
                            chat_pause_resume_flow(
                                session_id=session_id, 
                                initial_message=message,
                                flow_runs_dict=flow_runs
                            )
                        )
                        flow_tasks[session_id] = flow_task
                        
                        print(f"[WS] Flow started in background")
                        
                        # The flow will communicate via WebSocket
                        
                    except Exception as e:
                        print(f"[WS] Error starting flow: {e}")
                        import traceback
                        traceback.print_exc()
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Failed to start flow: {str(e)}"
                        })
                
                else:
                    # Resume existing flow
                    flow_run_id = flow_runs[session_id]
                    print(f"[WS] Attempting to resume flow {flow_run_id}")
                    print(f"[WS] Resume message: {message}")
                    
                    try:
                        async with get_client() as client:
                            # Resume the paused flow with the new message
                            flow_run = await client.read_flow_run(flow_run_id)
                            
                            if flow_run.state.is_paused():
                                print(f"[WS] Flow is paused, resuming with message: {message}")
                                await client.resume_flow_run(
                                    flow_run_id,
                                    run_input={"message": message}
                                )
                                print(f"[WS] Resume command sent successfully")
                            else:
                                print(f"[WS] Flow is in state: {flow_run.state.name}")
                                await websocket.send_json({
                                    "type": "status",
                                    "message": f"Flow is {flow_run.state.name}, cannot resume"
                                })
                            
                    except Exception as e:
                        print(f"[WS] Error resuming flow: {e}")
                        import traceback
                        traceback.print_exc()
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Failed to resume flow: {str(e)}"
                        })
                
    except WebSocketDisconnect:
        print(f"[WS] WebSocket disconnected: {session_id}")
    except Exception as e:
        print(f"[WS] WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        websocket_manager.pop(session_id, None)
        # Clean up but don't cancel the flow task - let it complete or timeout
        print(f"[WS] Cleaned up connection for {session_id}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)