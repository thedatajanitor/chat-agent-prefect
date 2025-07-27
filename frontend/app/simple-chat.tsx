'use client';

import { useState, useEffect, useRef, FormEvent } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export function SimpleChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const statusTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    const initializeChat = async () => {
      try {
        // Start a new chat session
        const response = await fetch('http://localhost:8000/api/chat/start', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        const data = await response.json();
        setSessionId(data.session_id);

        // Connect WebSocket
        const wsUrl = `ws://localhost:8000/ws/${data.session_id}`;
        ws.current = new WebSocket(wsUrl);

        ws.current.onopen = () => {
          setIsConnected(true);
          console.log('WebSocket connected');
        };

        ws.current.onmessage = (event) => {
          const data = JSON.parse(event.data);
          console.log('Received:', data);
          
          if (data.type === 'agent_message') {
            setMessages((prev) => [
              ...prev,
              {
                role: 'assistant',
                content: data.message,
                timestamp: data.timestamp,
              },
            ]);
            // Clear status when agent responds
            setStatus(null);
            setIsProcessing(false);
          } else if (data.type === 'status') {
            setStatus(data.message);
            // Clear "paused" status messages after a delay
            if (data.message.includes('paused') || data.message.includes('Send a message')) {
              if (statusTimeoutRef.current) {
                clearTimeout(statusTimeoutRef.current);
              }
              statusTimeoutRef.current = setTimeout(() => {
                setStatus(null);
                setIsProcessing(false);
              }, 2000);
            }
          } else if (data.type === 'task_status') {
            // Show task execution status
            setStatus(`${data.task}: ${data.message}`);
            setIsProcessing(true);
          } else if (data.type === 'flow_status') {
            // Handle flow status updates
            if (data.status === 'processing' || data.status === 'resumed') {
              setIsProcessing(true);
              setStatus(data.message);
            } else if (data.status === 'paused') {
              // Hide paused status after a short delay
              setStatus(data.message);
              if (statusTimeoutRef.current) {
                clearTimeout(statusTimeoutRef.current);
              }
              statusTimeoutRef.current = setTimeout(() => {
                setStatus(null);
                setIsProcessing(false);
              }, 2000);
            }
          }
        };

        ws.current.onclose = () => {
          setIsConnected(false);
          console.log('WebSocket disconnected');
        };

        ws.current.onerror = (error) => {
          console.error('WebSocket error:', error);
        };
      } catch (error) {
        console.error('Failed to initialize chat:', error);
      }
    };

    initializeChat();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
      if (statusTimeoutRef.current) {
        clearTimeout(statusTimeoutRef.current);
      }
    };
  }, []);

  const sendMessage = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !ws.current || ws.current.readyState !== WebSocket.OPEN) {
      return;
    }

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);

    ws.current.send(
      JSON.stringify({
        type: 'user_message',
        message: input,
      })
    );

    setInput('');
    setIsProcessing(true);
    setStatus('Processing...');
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[70%] rounded-lg p-3 ${
                message.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 text-gray-800'
              }`}
            >
              {message.content}
            </div>
          </div>
        ))}
      </div>
      {status && isProcessing && (
        <div className="px-4 py-2 bg-blue-50 text-blue-600 text-sm animate-pulse">
          {status}
        </div>
      )}
      <form onSubmit={sendMessage} className="p-4 border-t">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={!isConnected}
          />
          <button
            type="submit"
            disabled={!isConnected}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
        {!isConnected && (
          <p className="text-sm text-red-500 mt-2">Connecting to server...</p>
        )}
      </form>
    </div>
  );
}