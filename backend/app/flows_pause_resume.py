"""
Prefect flow designed for pause/resume chat conversations
"""
from prefect import flow, task, pause_flow_run, get_run_logger
from prefect.input import RunInput
from prefect.deployments import run_deployment
import asyncio
from datetime import datetime
from typing import Dict, Optional, Any
import httpx
import json
import os


class UserMessage(RunInput):
    """Input model for user messages during pause"""
    message: str


@task(name="send-websocket-update", log_prints=True)
async def send_websocket_update(session_id: str, update_type: str, data: dict):
    """Send updates to the WebSocket endpoint"""
    logger = get_run_logger()
    
    # Construct the URL for the internal API
    api_url = os.getenv("INTERNAL_API_URL", "http://localhost:8000")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/api/internal/websocket-update",
                json={
                    "session_id": session_id,
                    "type": update_type,
                    "data": data
                }
            )
            if response.status_code == 200:
                logger.info(f"Sent {update_type} update to {session_id}")
            else:
                logger.warning(f"Failed to send update: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending WebSocket update: {e}")


@task(name="process-message", log_prints=True)
async def process_message(message: str, session_id: str, interaction: int) -> Dict:
    """Process user message"""
    logger = get_run_logger()
    logger.info(f"Processing message #{interaction} for {session_id}: {message}")
    
    # Send status update
    await send_websocket_update(session_id, "task_status", {
        "task": "process-message",
        "status": "running",
        "message": f"Processing message #{interaction}..."
    })
    
    # Simulate processing
    await asyncio.sleep(2)
    
    # Send completion update
    await send_websocket_update(session_id, "task_status", {
        "task": "process-message",
        "status": "completed",
        "message": "Message processed"
    })
    
    return {
        "message": message,
        "word_count": len(message.split()),
        "interaction": interaction,
        "processed_at": datetime.now().isoformat()
    }


@task(name="analyze-sentiment", log_prints=True)
async def analyze_sentiment(context: Dict, session_id: str) -> str:
    """Analyze message sentiment"""
    logger = get_run_logger()
    logger.info(f"Analyzing sentiment for {session_id}")
    
    await send_websocket_update(session_id, "task_status", {
        "task": "analyze-sentiment",
        "status": "running",
        "message": "Analyzing sentiment..."
    })
    
    await asyncio.sleep(1.5)
    
    message = context["message"].lower()
    if "?" in message:
        sentiment = "curious"
    elif any(word in message for word in ["thanks", "great", "good", "love"]):
        sentiment = "positive"
    elif any(word in message for word in ["bad", "wrong", "issue", "problem"]):
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    await send_websocket_update(session_id, "task_status", {
        "task": "analyze-sentiment",
        "status": "completed",
        "message": f"Sentiment: {sentiment}"
    })
    
    logger.info(f"Sentiment detected: {sentiment}")
    return sentiment


@task(name="generate-response", log_prints=True)
async def generate_response(context: Dict, sentiment: str, session_id: str) -> str:
    """Generate agent response"""
    logger = get_run_logger()
    logger.info(f"Generating response for {session_id}")
    
    await send_websocket_update(session_id, "task_status", {
        "task": "generate-response",
        "status": "running",
        "message": "Generating response..."
    })
    
    await asyncio.sleep(2)
    
    interaction = context["interaction"]
    message = context["message"]
    
    if interaction == 1:
        response = f"Hello! I received your first message: '{message}' ({sentiment} sentiment). The flow is now paused. Send another message to resume!"
    elif interaction == 2:
        response = f"Great! The flow resumed successfully. Your message '{message}' shows {sentiment} sentiment. This is interaction #{interaction}."
    else:
        response = f"Interaction #{interaction}: I processed '{message}' with {sentiment} sentiment. The flow continues to pause/resume!"
    
    await send_websocket_update(session_id, "task_status", {
        "task": "generate-response",
        "status": "completed",
        "message": "Response generated"
    })
    
    logger.info(f"Generated response: {response}")
    return response


@flow(name="chat-pause-resume-flow", log_prints=True, persist_result=True)
async def chat_pause_resume_flow(
    session_id: str,
    initial_message: str,
    max_interactions: int = 10
) -> Dict[str, Any]:
    """
    Chat flow that pauses between user interactions
    """
    logger = get_run_logger()
    logger.info(f"Starting chat flow for session: {session_id}")
    logger.info(f"Initial message: {initial_message}")
    
    # Send flow start notification
    await send_websocket_update(session_id, "flow_status", {
        "status": "started",
        "message": "Chat flow started"
    })
    
    conversation_history = []
    interaction = 0
    message = initial_message
    
    while interaction < max_interactions:
        interaction += 1
        logger.info(f"\n=== Interaction {interaction} ===")
        
        # Send interaction start
        await send_websocket_update(session_id, "flow_status", {
            "status": "processing",
            "message": f"Processing interaction {interaction}",
            "interaction": interaction
        })
        
        # Execute tasks
        context = await process_message(message, session_id, interaction)
        sentiment = await analyze_sentiment(context, session_id)
        response = await generate_response(context, sentiment, session_id)
        
        # Send the agent response
        await send_websocket_update(session_id, "agent_message", {
            "message": response,
            "interaction": interaction,
            "sentiment": sentiment,
            "timestamp": datetime.now().isoformat()
        })
        
        # Store in history
        conversation_history.append({
            "interaction": interaction,
            "user": message,
            "agent": response,
            "sentiment": sentiment,
            "timestamp": datetime.now().isoformat()
        })
        
        # Check for exit
        if any(word in message.lower() for word in ["exit", "goodbye", "bye"]):
            logger.info("User requested exit")
            await send_websocket_update(session_id, "flow_status", {
                "status": "completed",
                "message": "Conversation ended. Thank you!"
            })
            break
        
        # Don't pause on the last allowed interaction
        if interaction >= max_interactions:
            await send_websocket_update(session_id, "flow_status", {
                "status": "completed",
                "message": "Maximum interactions reached"
            })
            break
        
        # Notify that we're pausing
        logger.info("Pausing flow to wait for user input...")
        await send_websocket_update(session_id, "flow_status", {
            "status": "paused",
            "message": "Flow paused. Send a message to resume...",
            "interaction": interaction
        })
        
        # PAUSE THE FLOW
        user_input = await pause_flow_run(
            wait_for_input=UserMessage,
            timeout=600  # 10 minute timeout
        )
        
        if not user_input:
            logger.info("Timeout waiting for user input")
            await send_websocket_update(session_id, "flow_status", {
                "status": "timeout",
                "message": "Flow timed out waiting for input"
            })
            break
        
        # Flow resumes here
        message = user_input.message
        logger.info(f"Flow resumed with message: {message}")
        
        await send_websocket_update(session_id, "flow_status", {
            "status": "resumed",
            "message": "Flow resumed!",
            "interaction": interaction + 1
        })
    
    # Final flow status
    await send_websocket_update(session_id, "flow_status", {
        "status": "completed",
        "message": "Chat flow completed",
        "total_interactions": interaction
    })
    
    return {
        "session_id": session_id,
        "total_interactions": interaction,
        "history": conversation_history,
        "completed_at": datetime.now().isoformat()
    }