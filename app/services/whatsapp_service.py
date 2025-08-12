from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from typing import Optional
from ..core.config import settings
from ..models.schemas import ChatMessage, Channel, WhatsAppMessage
from ..services.chatbot_service import chatbot_service
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WhatsAppService:
    def __init__(self):
        self.client: Optional[Client] = None
        self.is_initialized = False
        self.rate_limit_cache = {}  # Simple rate limiting
    
    def initialize(self):
        """Initialize Twilio client for WhatsApp"""
        if not all([
            settings.twilio_account_sid,
            settings.twilio_auth_token,
            settings.twilio_phone_number
        ]):
            logger.warning("Twilio credentials not configured")
            return False
        
        try:
            self.client = Client(
                settings.twilio_account_sid,
                settings.twilio_auth_token
            )
            
            # Test the connection by getting account info
            account = self.client.api.accounts(settings.twilio_account_sid).fetch()
            if account.status == 'active':
                self.is_initialized = True
                logger.info(f"WhatsApp service initialized for account: {account.friendly_name}")
                return True
            else:
                logger.error(f"Twilio account status: {account.status}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize WhatsApp service: {e}")
            return False
    
    async def send_message(self, to_number: str, message: str) -> Optional[str]:
        """Send WhatsApp message"""
        if not self.is_initialized:
            self.initialize()
        
        if not self.client:
            return None
        
        try:
            # Check rate limiting
            if not self._check_rate_limit(to_number):
                logger.warning(f"Rate limit exceeded for {to_number}")
                return None
            
            # Ensure proper WhatsApp formatting
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
            
            from_number = f'whatsapp:{settings.twilio_phone_number}'
            
            # Send message in thread pool since Twilio client is synchronous
            loop = asyncio.get_event_loop()
            twilio_message = await loop.run_in_executor(
                None,
                self._send_twilio_message,
                from_number,
                to_number,
                message
            )
            
            if twilio_message:
                self._update_rate_limit(to_number)
                return twilio_message.sid
            
            return None
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return None
    
    def _send_twilio_message(self, from_number: str, to_number: str, message: str):
        """Send message via Twilio (synchronous)"""
        try:
            return self.client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
        except TwilioException as e:
            logger.error(f"Twilio error: {e}")
            return None
    
    async def handle_message(self, whatsapp_message: WhatsAppMessage):
        """Handle incoming WhatsApp message"""
        try:
            # Extract phone number for user ID
            from_number = whatsapp_message.from_number
            user_phone = from_number.replace('whatsapp:', '').replace('+', '')
            
            # Create chat message
            chat_message = ChatMessage(
                message=whatsapp_message.body,
                user_id=f"whatsapp_{user_phone}",
                session_id=f"whatsapp_{user_phone}",
                channel=Channel.WHATSAPP,
                metadata={
                    "from_number": from_number,
                    "to_number": whatsapp_message.to_number,
                    "message_sid": whatsapp_message.message_sid,
                    "account_sid": whatsapp_message.account_sid
                }
            )
            
            # Process with chatbot
            response = await chatbot_service.process_message(chat_message)
            
            # Format response for WhatsApp (split long messages)
            formatted_responses = self._format_whatsapp_message(response.response)
            
            # Send response(s)
            for msg in formatted_responses:
                await self.send_message(from_number, msg)
                if len(formatted_responses) > 1:
                    # Small delay between messages
                    await asyncio.sleep(1)
            
            # Handle escalation
            if response.requires_escalation:
                escalation_msg = "A support agent will contact you shortly. Thank you for your patience! 🙏"
                await self.send_message(from_number, escalation_msg)
                
                # Notify internal systems
                await self._notify_escalation(whatsapp_message, response)
                
        except Exception as e:
            logger.error(f"Error handling WhatsApp message: {e}")
    
    def _format_whatsapp_message(self, message: str, max_length: int = 1600) -> list:
        """Format message for WhatsApp (split if too long)"""
        if len(message) <= max_length:
            return [message]
        
        # Split message into chunks
        messages = []
        words = message.split()
        current_message = ""
        
        for word in words:
            if len(current_message + " " + word) <= max_length:
                if current_message:
                    current_message += " " + word
                else:
                    current_message = word
            else:
                if current_message:
                    messages.append(current_message)
                    current_message = word
                else:
                    # Word is too long, split it
                    messages.append(word[:max_length])
                    current_message = word[max_length:]
        
        if current_message:
            messages.append(current_message)
        
        return messages
    
    def _check_rate_limit(self, phone_number: str, limit: int = 5, window_minutes: int = 1) -> bool:
        """Simple rate limiting check"""
        now = datetime.now()
        key = phone_number
        
        if key not in self.rate_limit_cache:
            self.rate_limit_cache[key] = []
        
        # Clean old entries
        self.rate_limit_cache[key] = [
            timestamp for timestamp in self.rate_limit_cache[key]
            if now - timestamp < timedelta(minutes=window_minutes)
        ]
        
        # Check if under limit
        if len(self.rate_limit_cache[key]) < limit:
            return True
        
        return False
    
    def _update_rate_limit(self, phone_number: str):
        """Update rate limit cache"""
        now = datetime.now()
        key = phone_number
        
        if key not in self.rate_limit_cache:
            self.rate_limit_cache[key] = []
        
        self.rate_limit_cache[key].append(now)
    
    async def _notify_escalation(self, whatsapp_message: WhatsAppMessage, response):
        """Notify internal systems of escalation"""
        try:
            # This could send to Slack, email, or internal dashboard
            logger.info(f"WhatsApp escalation for {whatsapp_message.from_number}: {whatsapp_message.body}")
            
            # Example: Send to Slack if available
            from .slack_service import slack_service
            if slack_service.is_initialized:
                escalation_text = f"📱 *WhatsApp Escalation*\n\n" \
                                 f"*From:* {whatsapp_message.from_number}\n" \
                                 f"*Message:* {whatsapp_message.body}\n" \
                                 f"*Intent:* {response.intent}\n" \
                                 f"*Confidence:* {response.confidence:.2f}\n" \
                                 f"*Message SID:* {whatsapp_message.message_sid}"
                
                # Send to admin channel
                admin_channel = "#customer-support-escalations"
                await slack_service.send_message(admin_channel, escalation_text)
                
        except Exception as e:
            logger.error(f"Error sending escalation notification: {e}")
    
    async def send_template_message(
        self, 
        to_number: str, 
        template_name: str, 
        template_params: Optional[list] = None
    ) -> Optional[str]:
        """Send WhatsApp template message (for business accounts)"""
        if not self.is_initialized:
            self.initialize()
        
        if not self.client:
            return None
        
        try:
            # This would be used for pre-approved templates
            # Implementation depends on your Twilio setup and approved templates
            logger.info(f"Template message feature not implemented: {template_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error sending template message: {e}")
            return None
    
    def create_welcome_message(self) -> str:
        """Create welcome message for new users"""
        return ("👋 Welcome to our Customer Support!\n\n"
                "I'm your AI assistant and I can help you with:\n\n"
                "📦 Order tracking\n"
                "👤 Account information\n"
                "💳 Billing questions\n"
                "🔧 Technical support\n\n"
                "Just send me a message describing what you need help with! 😊")
    
    async def send_welcome_message(self, to_number: str) -> Optional[str]:
        """Send welcome message to new user"""
        welcome_msg = self.create_welcome_message()
        return await self.send_message(to_number, welcome_msg)


# Global WhatsApp service instance
whatsapp_service = WhatsAppService()
