from typing import Dict, Any, List
from datetime import datetime
import random


class SimpleAgent:
    """Simple chat agent for demonstration purposes"""
    
    def __init__(self):
        self.conversation_history: List[Dict[str, str]] = []
        self.responses = [
            "I understand. Can you tell me more about that?",
            "That's interesting! What else would you like to know?",
            "I'm here to help. What specific aspect would you like to explore?",
            "Thank you for sharing that. How can I assist you further?",
            "I see what you mean. Let me help you with that.",
        ]
    
    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process the user's message and extract context"""
        
        # Update conversation history
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Simple context extraction
        context = {
            "message_length": len(message),
            "is_question": "?" in message,
            "end_conversation": any(word in message.lower() for word in ["goodbye", "bye", "exit", "quit"]),
            "timestamp": datetime.now().isoformat()
        }
        
        return context
    
    async def generate_response(self, context: Dict[str, Any]) -> str:
        """Generate a response based on context"""
        
        # Check if conversation should end
        if context.get("end_conversation", False):
            return "Thank you for chatting! Have a great day!"
        
        # Get the last user message
        last_message = self.conversation_history[-1]["content"] if self.conversation_history else ""
        
        # Generate a simple response
        if context.get("is_question"):
            response = f"You asked: '{last_message}'. {random.choice(self.responses)}"
        else:
            response = random.choice(self.responses)
        
        # Update conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })
        
        return response
    
    def reset(self):
        """Reset the agent's state"""
        self.conversation_history = []