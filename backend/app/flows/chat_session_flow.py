from prefect import flow, task, pause_flow_run, resume_flow_run
from prefect.runtime import flow_run
from prefect.states import Paused
import asyncio
from datetime import datetime
import random
from typing import Dict, Any, Optional


@task(name="process-user-input")
async def process_user_input(message: str, session_id: str) -> Dict[str, Any]:
    """Process the user's input message"""
    print(f"[{session_id}] Processing user message: {message}")
    
    # Simulate processing time
    await asyncio.sleep(1)
    
    return {
        "original_message": message,
        "word_count": len(message.split()),
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id
    }


@task(name="analyze-sentiment")
async def analyze_sentiment(context: Dict[str, Any]) -> str:
    """Analyze the sentiment of the message"""
    print(f"[{context['session_id']}] Analyzing sentiment...")
    
    # Simulate analysis time
    await asyncio.sleep(1.5)
    
    # Mock sentiment analysis
    sentiments = ["positive", "neutral", "negative", "curious", "excited"]
    return random.choice(sentiments)


@task(name="fetch-context")
async def fetch_relevant_context(context: Dict[str, Any], sentiment: str) -> Dict[str, Any]:
    """Fetch relevant context based on the message and sentiment"""
    print(f"[{context['session_id']}] Fetching relevant context for {sentiment} sentiment...")
    
    # Simulate API call or database query
    await asyncio.sleep(2)
    
    context["sentiment"] = sentiment
    context["additional_context"] = f"Context data for {sentiment} message"
    return context


@task(name="generate-response")
async def generate_agent_response(context: Dict[str, Any]) -> str:
    """Generate the agent's response"""
    print(f"[{context['session_id']}] Generating response...")
    
    # Simulate response generation time
    await asyncio.sleep(1)
    
    responses = [
        f"I understand you said '{context['original_message']}'. The sentiment seems {context['sentiment']}.",
        f"Thank you for your message. I detected a {context['sentiment']} tone. How can I help further?",
        f"Interesting! Your message has {context['word_count']} words and a {context['sentiment']} sentiment.",
        f"Based on your {context['sentiment']} message, I'd like to know more about your thoughts."
    ]
    
    return random.choice(responses)


@task(name="log-interaction")
async def log_interaction(session_id: str, user_message: str, agent_response: str):
    """Log the interaction for analytics"""
    print(f"[{session_id}] Logging interaction:")
    print(f"  User: {user_message}")
    print(f"  Agent: {agent_response}")
    
    # Simulate logging time
    await asyncio.sleep(0.5)


@flow(name="chat-session-flow", persist_result=True)
async def chat_session_flow(session_id: str, initial_message: Optional[str] = None):
    """
    Main chat session flow that processes messages and pauses between interactions
    """
    conversation_history = []
    interaction_count = 0
    
    # If we're resuming, get the message from the resume data
    if initial_message is None:
        # This means we're resuming from a pause
        resume_data = flow_run.parameters.get("resume_data", {})
        message = resume_data.get("message", "")
        conversation_history = resume_data.get("history", [])
        interaction_count = resume_data.get("interaction_count", 0)
    else:
        message = initial_message
    
    while True:
        interaction_count += 1
        print(f"\n=== Interaction {interaction_count} ===")
        
        # Task 1: Process the user input
        context = await process_user_input(message, session_id)
        
        # Task 2: Analyze sentiment (runs after task 1)
        sentiment = await analyze_sentiment(context)
        
        # Task 3: Fetch relevant context (runs after task 2)
        enriched_context = await fetch_relevant_context(context, sentiment)
        
        # Task 4: Generate response (runs after task 3)
        agent_response = await generate_agent_response(enriched_context)
        
        # Task 5: Log the interaction
        await log_interaction(session_id, message, agent_response)
        
        # Update conversation history
        conversation_history.append({
            "user": message,
            "agent": agent_response,
            "timestamp": datetime.now().isoformat(),
            "interaction": interaction_count
        })
        
        # Send response back (this will be handled by the caller)
        print(f"[{session_id}] Response ready: {agent_response}")
        
        # Check if we should end the conversation
        if "goodbye" in message.lower() or "exit" in message.lower():
            print(f"[{session_id}] Ending conversation after {interaction_count} interactions")
            return {
                "session_id": session_id,
                "final_response": agent_response,
                "total_interactions": interaction_count,
                "conversation_ended": True,
                "history": conversation_history
            }
        
        # Pause the flow and wait for the next user input
        print(f"[{session_id}] Pausing flow to wait for user input...")
        pause_data = await pause_flow_run(
            wait_for_input=True,
            pause_key=f"session_{session_id}_{interaction_count}"
        )
        
        # When resumed, extract the new message
        if pause_data:
            message = pause_data.get("message", "")
            # Store conversation state in case we need it
            pause_data["history"] = conversation_history
            pause_data["interaction_count"] = interaction_count
        else:
            print(f"[{session_id}] No resume data received, ending flow")
            break
        
        # Return the response so it can be sent to the user
        yield {
            "response": agent_response,
            "interaction": interaction_count,
            "continue": True
        }