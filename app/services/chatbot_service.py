import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from ..models.schemas import (
    ChatMessage, ChatResponse, ChatHistory, MessageType, 
    IntentType, UserContext, Channel
)
from ..core.database import get_chat_history_collection, get_user_context_collection
from ..core.cache import cache_manager
from .nlp_service import nlp_service
from .salesforce_service import salesforce_service
import logging

logger = logging.getLogger(__name__)


class ChatbotService:
    def __init__(self):
        self.response_templates = self._load_response_templates()
        self.escalation_phrases = [
            "I understand your frustration. Let me connect you with one of our human agents who can provide more personalized assistance.",
            "This seems like a complex issue. I'm transferring you to a human agent who can help you better.",
            "I want to make sure you get the best possible help. Let me escalate this to our support team."
        ]
    
    async def process_message(self, message: ChatMessage) -> ChatResponse:
        """Process incoming chat message and generate response"""
        start_time = datetime.now()
        
        try:
            # Generate session ID if not provided
            session_id = message.session_id or str(uuid.uuid4())
            
            # Get or create user context
            user_context = await self._get_user_context(message.user_id)
            user_context.current_session = session_id
            user_context.last_interaction = datetime.utcnow()
            
            # Check for cached frequent queries
            message_hash = nlp_service.generate_message_hash(message.message)
            cached_response = await cache_manager.get_frequent_query_response(message_hash)
            
            if cached_response and not self._is_personalized_query(message.message):
                # Increment query count for analytics
                await cache_manager.increment_query_count(message_hash)
                
                response = ChatResponse(
                    response=cached_response,
                    intent="cached",
                    confidence=1.0,
                    requires_escalation=False,
                    session_id=session_id,
                    response_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                )
                
                # Store in chat history
                await self._store_chat_history(message, response, user_context)
                return response
            
            # Predict intent using NLP service
            intent_prediction = await nlp_service.predict_intent(message.message)
            
            # Check if escalation is needed
            requires_escalation = await nlp_service.is_escalation_needed(
                message.message, 
                intent_prediction.confidence
            )
            
            if requires_escalation:
                response_text = self._get_escalation_response()
            else:
                # Generate response based on intent
                response_text = await self._generate_response(
                    intent_prediction, 
                    message, 
                    user_context
                )
            
            response = ChatResponse(
                response=response_text,
                intent=intent_prediction.intent.value,
                confidence=intent_prediction.confidence,
                requires_escalation=requires_escalation,
                session_id=session_id,
                response_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
            
            # Store chat history
            await self._store_chat_history(message, response, user_context)
            
            # Update user context
            await self._update_user_context(user_context)
            
            # Cache frequent queries
            await self._cache_if_frequent(message_hash, response_text)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return ChatResponse(
                response="I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
                intent="error",
                confidence=0.0,
                requires_escalation=True,
                session_id=session_id or str(uuid.uuid4()),
                response_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
    
    async def _generate_response(
        self, 
        intent_prediction, 
        message: ChatMessage, 
        user_context: UserContext
    ) -> str:
        """Generate response based on intent and context"""
        
        intent = intent_prediction.intent
        entities = intent_prediction.entities
        
        # Get customer data from Salesforce if available
        customer_data = None
        if 'email' in entities:
            customer_data = await salesforce_service.get_customer_summary(entities['email'])
        elif user_context.customer_id:
            # Use cached customer ID
            pass
        
        # Generate response based on intent
        if intent == IntentType.ORDER_INQUIRY:
            return await self._handle_order_inquiry(entities, customer_data, user_context)
        
        elif intent == IntentType.ACCOUNT_INFO:
            return await self._handle_account_info(entities, customer_data, user_context)
        
        elif intent == IntentType.PRODUCT_INFO:
            return await self._handle_product_info(entities, user_context)
        
        elif intent == IntentType.BILLING:
            return await self._handle_billing_inquiry(entities, customer_data, user_context)
        
        elif intent == IntentType.TECHNICAL_SUPPORT:
            return await self._handle_technical_support(entities, customer_data, user_context)
        
        elif intent == IntentType.ESCALATE:
            return self._get_escalation_response()
        
        else:  # GENERAL
            return await self._handle_general_inquiry(message.message, user_context)
    
    async def _handle_order_inquiry(self, entities: Dict, customer_data: Dict, user_context: UserContext) -> str:
        """Handle order-related inquiries"""
        
        if 'order_number' in entities:
            order_number = entities['order_number']
            
            if customer_data and customer_data.get('contact'):
                # Get specific order information from Salesforce
                orders = await salesforce_service.get_contact_orders(customer_data['contact']['id'])
                matching_orders = [o for o in orders if order_number in o.order_number]
                
                if matching_orders:
                    order = matching_orders[0]
                    return f"I found your order #{order.order_number}. The current status is '{order.status}'. " \
                           f"Order date: {order.order_date.strftime('%B %d, %Y') if order.order_date else 'N/A'}. " \
                           f"Is there anything specific you'd like to know about this order?"
                else:
                    return f"I couldn't find order #{order_number} in our system. " \
                           f"Please double-check the order number or provide your email address so I can help you better."
            else:
                return f"To help you track order #{order_number}, I'll need your email address. " \
                       f"Could you please provide the email address associated with your account?"
        
        else:
            if customer_data and customer_data.get('recent_orders', 0) > 0:
                return f"I can help you with order information. You have {customer_data['recent_orders']} recent orders. " \
                       f"Could you provide the specific order number you're asking about?"
            else:
                return "I can help you track your orders. Could you please provide your order number and " \
                       "the email address associated with your account?"
    
    async def _handle_account_info(self, entities: Dict, customer_data: Dict, user_context: UserContext) -> str:
        """Handle account-related inquiries"""
        
        if customer_data and customer_data.get('contact'):
            contact = customer_data['contact']
            return f"Here's your account information:\n" \
                   f"Name: {contact['name']}\n" \
                   f"Email: {contact.get('email', 'N/A')}\n" \
                   f"Phone: {contact.get('phone', 'N/A')}\n" \
                   f"Customer Tier: {customer_data.get('customer_tier', 'Standard')}\n" \
                   f"Total Orders: {customer_data.get('total_orders', 0)}\n\n" \
                   f"Is there something specific you'd like to update?"
        else:
            return "To access your account information, I'll need to verify your identity. " \
                   "Could you please provide the email address associated with your account?"
    
    async def _handle_product_info(self, entities: Dict, user_context: UserContext) -> str:
        """Handle product information inquiries"""
        
        if 'product' in entities:
            product = entities['product'].title()
            return f"I can help you with information about {product}. Here are some common questions:\n\n" \
                   f"• Product specifications and features\n" \
                   f"• Pricing and availability\n" \
                   f"• Compatibility and requirements\n" \
                   f"• Warranty information\n\n" \
                   f"What specific information would you like to know about {product}?"
        else:
            return "I can help you find product information. What product are you interested in learning about?"
    
    async def _handle_billing_inquiry(self, entities: Dict, customer_data: Dict, user_context: UserContext) -> str:
        """Handle billing-related inquiries"""
        
        if customer_data and customer_data.get('contact'):
            return f"I can help you with billing questions. Based on your account, I can see you have " \
                   f"{customer_data.get('total_orders', 0)} orders on record.\n\n" \
                   f"For detailed billing information and payment history, I can:\n" \
                   f"• Help you understand charges on your recent orders\n" \
                   f"• Provide information about payment methods\n" \
                   f"• Assist with refund requests\n\n" \
                   f"What specific billing question can I help you with?"
        else:
            return "I can help you with billing questions. To access your billing information, " \
                   "I'll need to verify your account. Could you provide your email address?"
    
    async def _handle_technical_support(self, entities: Dict, customer_data: Dict, user_context: UserContext) -> str:
        """Handle technical support inquiries"""
        
        if 'product' in entities:
            product = entities['product'].title()
            return f"I can help troubleshoot issues with your {product}. Here are some quick solutions:\n\n" \
                   f"• Try restarting the device\n" \
                   f"• Check for software updates\n" \
                   f"• Verify all connections are secure\n\n" \
                   f"Could you describe the specific issue you're experiencing with your {product}?"
        else:
            return "I'm here to help with technical issues. Could you please describe:\n\n" \
                   f"• What product or service you're having trouble with\n" \
                   f"• What specific problem you're experiencing\n" \
                   f"• Any error messages you're seeing\n\n" \
                   f"This will help me provide the best assistance."
    
    async def _handle_general_inquiry(self, message: str, user_context: UserContext) -> str:
        """Handle general inquiries"""
        
        greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        thanks = ['thank', 'thanks', 'appreciate']
        
        message_lower = message.lower()
        
        if any(greeting in message_lower for greeting in greetings):
            return "Hello! I'm your AI customer support assistant. I can help you with:\n\n" \
                   "• Order tracking and delivery information\n" \
                   "• Account information and updates\n" \
                   "• Product information and specifications\n" \
                   "• Billing and payment questions\n" \
                   "• Technical support\n\n" \
                   "How can I assist you today?"
        
        elif any(thank in message_lower for thank in thanks):
            return "You're welcome! Is there anything else I can help you with today?"
        
        else:
            return "I'm here to help! I can assist you with orders, account information, products, " \
                   "billing, and technical support. Could you please let me know what you need help with?"
    
    def _get_escalation_response(self) -> str:
        """Get random escalation response"""
        import random
        return random.choice(self.escalation_phrases)
    
    async def _get_user_context(self, user_id: str) -> UserContext:
        """Get or create user context"""
        try:
            # Try to get from cache first
            cached_context = await cache_manager.get_user_context(user_id)
            if cached_context:
                return UserContext(**cached_context)
            
            # Try to get from database
            collection = get_user_context_collection()
            context_doc = await collection.find_one({"user_id": user_id})
            
            if context_doc:
                # Remove MongoDB _id field
                context_doc.pop('_id', None)
                context = UserContext(**context_doc)
            else:
                # Create new context
                context = UserContext(user_id=user_id)
            
            # Cache the context
            await cache_manager.cache_user_context(user_id, context.dict())
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return UserContext(user_id=user_id)
    
    async def _update_user_context(self, user_context: UserContext):
        """Update user context in database and cache"""
        try:
            user_context.updated_at = datetime.utcnow()
            
            collection = get_user_context_collection()
            await collection.update_one(
                {"user_id": user_context.user_id},
                {"$set": user_context.dict()},
                upsert=True
            )
            
            # Update cache
            await cache_manager.cache_user_context(user_context.user_id, user_context.dict())
            
        except Exception as e:
            logger.error(f"Error updating user context: {e}")
    
    async def _store_chat_history(self, message: ChatMessage, response: ChatResponse, user_context: UserContext):
        """Store chat interaction in history"""
        try:
            # Store user message
            user_history = ChatHistory(
                user_id=message.user_id,
                session_id=response.session_id,
                message=message.message,
                response="",
                message_type=MessageType.USER,
                intent=response.intent,
                confidence=response.confidence,
                channel=message.channel,
                metadata=message.metadata or {}
            )
            
            # Store bot response
            bot_history = ChatHistory(
                user_id=message.user_id,
                session_id=response.session_id,
                message="",
                response=response.response,
                message_type=MessageType.BOT,
                intent=response.intent,
                confidence=response.confidence,
                channel=message.channel,
                metadata={"response_time_ms": response.response_time_ms}
            )
            
            collection = get_chat_history_collection()
            await collection.insert_many([
                user_history.dict(exclude={'id'}),
                bot_history.dict(exclude={'id'})
            ])
            
        except Exception as e:
            logger.error(f"Error storing chat history: {e}")
    
    async def _cache_if_frequent(self, message_hash: str, response: str):
        """Cache response if query is frequent"""
        try:
            count = await cache_manager.increment_query_count(message_hash)
            if count and count >= 3:  # Cache after 3 occurrences
                await cache_manager.cache_frequent_query(message_hash, response)
                logger.info(f"Cached frequent query with hash {message_hash}")
        except Exception as e:
            logger.error(f"Error caching frequent query: {e}")
    
    def _is_personalized_query(self, message: str) -> bool:
        """Check if query requires personalized data"""
        personal_indicators = [
            'my order', 'my account', 'my profile', 'my payment',
            'order number', 'tracking number', '@', 'email'
        ]
        message_lower = message.lower()
        return any(indicator in message_lower for indicator in personal_indicators)
    
    def _load_response_templates(self) -> Dict[str, List[str]]:
        """Load response templates for different intents"""
        return {
            IntentType.ORDER_INQUIRY.value: [
                "I can help you track your order. Could you provide your order number?",
                "Let me look up your order information. What's your order number?",
            ],
            IntentType.ACCOUNT_INFO.value: [
                "I can help you with your account. Could you provide your email address?",
                "Let me access your account information. What's your registered email?",
            ],
            IntentType.PRODUCT_INFO.value: [
                "I'm happy to help with product information. What product are you interested in?",
                "I can provide product details. Which product would you like to know about?",
            ],
            IntentType.BILLING.value: [
                "I can help with billing questions. Could you provide your account email?",
                "Let me assist you with billing. What's your registered email address?",
            ],
            IntentType.TECHNICAL_SUPPORT.value: [
                "I'm here to help with technical issues. Could you describe the problem?",
                "Let me help troubleshoot. What technical issue are you experiencing?",
            ]
        }
    
    async def get_chat_history(self, user_id: str, session_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get chat history for a user"""
        try:
            collection = get_chat_history_collection()
            
            query = {"user_id": user_id}
            if session_id:
                query["session_id"] = session_id
            
            cursor = collection.find(query).sort("timestamp", -1).limit(limit)
            history = []
            
            async for doc in cursor:
                doc['id'] = str(doc.pop('_id'))
                history.append(doc)
            
            return list(reversed(history))  # Return in chronological order
            
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []


# Global chatbot service instance
chatbot_service = ChatbotService()
