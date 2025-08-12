from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('chatbot.log')
    ]
)

logger = logging.getLogger(__name__)

# Import core modules
from .core.config import settings
from .core.database import connect_to_mongo, close_mongo_connection
from .core.cache import cache_manager
from .services.nlp_service import nlp_service
from .services.salesforce_service import salesforce_service

# Import API routes
from .api.routes.chat import router as chat_router
from .api.routes.webhooks import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting AI-Powered Customer Support Chatbot...")
    
    try:
        # Connect to MongoDB
        await connect_to_mongo()
        
        # Connect to Redis
        await cache_manager.connect()
        
        # Initialize NLP service
        await nlp_service.initialize()
        
        # Connect to Salesforce
        await salesforce_service.connect()
        
        logger.info("All services initialized successfully!")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down services...")
    
    try:
        await close_mongo_connection()
        await cache_manager.disconnect()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="AI-Powered Customer Support Chatbot",
    description="An intelligent customer support chatbot with Salesforce CRM integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(webhook_router, prefix="/api", tags=["webhooks"])

# Serve static files (for web interface)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Root endpoint with basic information"""
    return {
        "name": "AI-Powered Customer Support Chatbot",
        "version": "1.0.0",
        "description": "Intelligent customer support with Salesforce CRM integration",
        "endpoints": {
            "chat": "/api/chat",
            "history": "/api/chat/history/{user_id}",
            "health": "/api/health",
            "docs": "/docs",
            "chat_ui": "/chat"
        }
    }


@app.get("/chat", response_class=HTMLResponse)
async def chat_interface():
    """Simple web chat interface"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Customer Support Chatbot</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .chat-container {
                max-width: 600px;
                margin: 0 auto;
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .chat-header {
                background-color: #007bff;
                color: white;
                padding: 15px;
                text-align: center;
            }
            .chat-messages {
                height: 400px;
                overflow-y: auto;
                padding: 20px;
                border-bottom: 1px solid #eee;
            }
            .message {
                margin-bottom: 15px;
                padding: 10px;
                border-radius: 5px;
                max-width: 80%;
            }
            .user-message {
                background-color: #e3f2fd;
                margin-left: auto;
                text-align: right;
            }
            .bot-message {
                background-color: #f1f1f1;
                margin-right: auto;
            }
            .chat-input {
                padding: 20px;
                display: flex;
                gap: 10px;
            }
            #messageInput {
                flex: 1;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
            }
            #sendButton {
                padding: 10px 20px;
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            #sendButton:hover {
                background-color: #0056b3;
            }
            #sendButton:disabled {
                background-color: #ccc;
                cursor: not-allowed;
            }
            .loading {
                color: #666;
                font-style: italic;
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">
                <h2>Customer Support Chatbot</h2>
                <p>How can I help you today?</p>
            </div>
            <div class="chat-messages" id="chatMessages">
                <div class="message bot-message">
                    Hello! I'm your AI customer support assistant. I can help you with orders, account information, billing, technical support, and more. What can I help you with today?
                </div>
            </div>
            <div class="chat-input">
                <input type="text" id="messageInput" placeholder="Type your message..." 
                       onkeypress="handleKeyPress(event)">
                <button id="sendButton" onclick="sendMessage()">Send</button>
            </div>
        </div>

        <script>
            const chatMessages = document.getElementById('chatMessages');
            const messageInput = document.getElementById('messageInput');
            const sendButton = document.getElementById('sendButton');
            
            // Generate a simple user ID
            const userId = 'web_' + Math.random().toString(36).substr(2, 9);

            function addMessage(message, isUser = false) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
                messageDiv.innerHTML = message.replace(/\\n/g, '<br>');
                chatMessages.appendChild(messageDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }

            function handleKeyPress(event) {
                if (event.key === 'Enter') {
                    sendMessage();
                }
            }

            async function sendMessage() {
                const message = messageInput.value.trim();
                if (!message) return;

                // Disable input
                messageInput.disabled = true;
                sendButton.disabled = true;
                sendButton.textContent = 'Sending...';

                // Add user message
                addMessage(message, true);
                messageInput.value = '';

                // Add loading indicator
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'message bot-message loading';
                loadingDiv.textContent = 'Typing...';
                chatMessages.appendChild(loadingDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;

                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            message: message,
                            user_id: userId,
                            channel: 'web'
                        })
                    });

                    const data = await response.json();
                    
                    // Remove loading indicator
                    chatMessages.removeChild(loadingDiv);
                    
                    if (response.ok) {
                        addMessage(data.response);
                        
                        if (data.requires_escalation) {
                            setTimeout(() => {
                                addMessage("I'm connecting you with a human agent now. Please hold on...");
                            }, 1000);
                        }
                    } else {
                        addMessage("I'm sorry, I encountered an error. Please try again.");
                    }

                } catch (error) {
                    console.error('Error:', error);
                    // Remove loading indicator
                    chatMessages.removeChild(loadingDiv);
                    addMessage("I'm sorry, I'm having trouble connecting. Please try again.");
                }

                // Re-enable input
                messageInput.disabled = false;
                sendButton.disabled = false;
                sendButton.textContent = 'Send';
                messageInput.focus();
            }

            // Focus on input when page loads
            messageInput.focus();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors"""
    return {
        "error": "Not Found",
        "message": f"The requested URL {request.url.path} was not found",
        "available_endpoints": [
            "/",
            "/api/chat",
            "/api/health",
            "/api/chat/history/{user_id}",
            "/chat",
            "/docs"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )