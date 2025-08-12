from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from typing import Optional, Dict, Any
from ..core.config import settings
from ..models.schemas import ChatMessage, Channel
from ..services.chatbot_service import chatbot_service
import logging
import asyncio

logger = logging.getLogger(__name__)


class SlackService:
    def __init__(self):
        self.client: Optional[AsyncWebClient] = None
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize Slack client"""
        if not settings.slack_bot_token:
            logger.warning("Slack bot token not configured")
            return False
        
        try:
            self.client = AsyncWebClient(token=settings.slack_bot_token)
            
            # Test the connection
            response = await self.client.auth_test()
            if response["ok"]:
                self.is_initialized = True
                logger.info(f"Slack service initialized for bot: {response['user']}")
                return True
            else:
                logger.error("Failed to authenticate with Slack")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize Slack service: {e}")
            return False
    
    async def send_message(
        self, 
        channel: str, 
        text: str, 
        thread_ts: Optional[str] = None,
        blocks: Optional[list] = None
    ) -> Optional[str]:
        """Send a message to Slack"""
        if not self.is_initialized:
            await self.initialize()
        
        if not self.client:
            return None
        
        try:
            response = await self.client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts,
                blocks=blocks
            )
            
            if response["ok"]:
                return response["ts"]
            else:
                logger.error(f"Failed to send Slack message: {response['error']}")
                return None
                
        except SlackApiError as e:
            logger.error(f"Slack API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")
            return None
    
    async def handle_message(self, event: Dict[str, Any]):
        """Handle incoming Slack message"""
        try:
            user_id = event.get('user')
            channel_id = event.get('channel')
            text = event.get('text', '')
            thread_ts = event.get('thread_ts')
            ts = event.get('ts')
            
            # Skip bot messages and empty messages
            if event.get('bot_id') or not text or not user_id:
                return
            
            # Create chat message
            chat_message = ChatMessage(
                message=text,
                user_id=f"slack_{user_id}",
                session_id=f"slack_{channel_id}_{thread_ts or ts}",
                channel=Channel.SLACK,
                metadata={
                    "slack_channel": channel_id,
                    "slack_user": user_id,
                    "thread_ts": thread_ts,
                    "ts": ts
                }
            )
            
            # Process with chatbot
            response = await chatbot_service.process_message(chat_message)
            
            # Send response back to Slack
            await self.send_message(
                channel=channel_id,
                text=response.response,
                thread_ts=thread_ts
            )
            
            # If escalation is needed, notify admin channel
            if response.requires_escalation:
                await self._notify_escalation(channel_id, user_id, text, response)
                
        except Exception as e:
            logger.error(f"Error handling Slack message: {e}")
    
    async def _notify_escalation(self, channel: str, user: str, original_message: str, response):
        """Notify admin channel of escalation"""
        try:
            escalation_text = f"🚨 *Escalation Required*\n\n" \
                             f"*User:* <@{user}>\n" \
                             f"*Channel:* <#{channel}>\n" \
                             f"*Original Message:* {original_message}\n" \
                             f"*Intent:* {response.intent}\n" \
                             f"*Confidence:* {response.confidence:.2f}"
            
            # Send to a designated admin channel (configure as needed)
            admin_channel = "#customer-support-escalations"  # Configure this
            
            await self.send_message(
                channel=admin_channel,
                text=escalation_text
            )
            
        except Exception as e:
            logger.error(f"Error sending escalation notification: {e}")
    
    async def create_interactive_message(self, channel: str, blocks: list) -> Optional[str]:
        """Send interactive message with blocks"""
        return await self.send_message(channel=channel, text="", blocks=blocks)
    
    def create_help_blocks(self) -> list:
        """Create help message blocks"""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Hello! I'm your AI Customer Support Assistant* 🤖\n\nI can help you with:"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*📦 Order Tracking*\nCheck order status and delivery information"
                    },
                    {
                        "type": "mrkdwn", 
                        "text": "*👤 Account Information*\nUpdate profile and account settings"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*💳 Billing Support*\nPayment questions and billing inquiries"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*🔧 Technical Support*\nTroubleshooting and technical issues"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Just type your question and I'll do my best to help! 😊"
                }
            }
        ]
    
    async def send_help_message(self, channel: str) -> Optional[str]:
        """Send interactive help message"""
        blocks = self.create_help_blocks()
        return await self.create_interactive_message(channel, blocks)


# Global Slack service instance  
slack_service = SlackService()
