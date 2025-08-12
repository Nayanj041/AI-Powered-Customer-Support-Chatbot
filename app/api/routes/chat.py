from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from ...models.schemas import ChatMessage, ChatResponse, HealthResponse
from ...services.chatbot_service import chatbot_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def send_message(message: ChatMessage):
    """
    Send a message to the chatbot and get a response
    """
    try:
        response = await chatbot_service.process_message(message)
        return response
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your message"
        )


@router.get("/chat/history/{user_id}")
async def get_chat_history(
    user_id: str,
    session_id: Optional[str] = None,
    limit: int = 50
):
    """
    Get chat history for a user
    """
    try:
        if limit > 100:
            limit = 100  # Prevent excessive data retrieval
        
        history = await chatbot_service.get_chat_history(
            user_id=user_id,
            session_id=session_id,
            limit=limit
        )
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "history": history,
            "count": len(history)
        }
    
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving chat history"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    """
    try:
        from ...core.database import db
        from ...core.cache import cache_manager
        from ...services.nlp_service import nlp_service
        from ...services.salesforce_service import salesforce_service
        
        services = {}
        
        # Check database connection
        try:
            if db.database:
                await db.database.command('ping')
                services["mongodb"] = "healthy"
            else:
                services["mongodb"] = "disconnected"
        except Exception as e:
            services["mongodb"] = f"unhealthy: {str(e)}"
        
        # Check Redis connection
        try:
            if cache_manager.redis:
                await cache_manager.redis.ping()
                services["redis"] = "healthy"
            else:
                services["redis"] = "disconnected"
        except Exception as e:
            services["redis"] = f"unhealthy: {str(e)}"
        
        # Check NLP service
        services["nlp"] = "ready" if nlp_service.is_initialized else "initializing"
        
        # Check Salesforce connection
        services["salesforce"] = "connected" if salesforce_service.is_connected else "disconnected"
        
        return HealthResponse(services=services)
    
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")
