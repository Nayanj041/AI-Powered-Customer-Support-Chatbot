from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
import json
import hashlib
import hmac
from ...models.schemas import SlackEvent, WhatsAppMessage, ChatMessage, Channel
from ...services.chatbot_service import chatbot_service
from ...core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhooks/slack")
async def slack_webhook(
    request: Request,
    x_slack_signature: Optional[str] = Header(None),
    x_slack_request_timestamp: Optional[str] = Header(None)
):
    """
    Handle Slack webhook events
    """
    try:
        body = await request.body()
        
        # Verify Slack signature if configured
        if settings.slack_signing_secret and x_slack_signature and x_slack_request_timestamp:
            if not _verify_slack_signature(body, x_slack_signature, x_slack_request_timestamp):
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse the request
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            # Handle URL-encoded form data
            form_data = await request.form()
            data = dict(form_data)
            if 'payload' in data:
                data = json.loads(data['payload'])
        
        # Handle URL verification challenge
        if data.get('type') == 'url_verification':
            return {"challenge": data.get('challenge')}
        
        # Handle message events
        if data.get('type') == 'event_callback':
            event = data.get('event', {})
            
            if event.get('type') == 'message' and not event.get('bot_id'):
                # Avoid responding to bot messages
                await _handle_slack_message(event)
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Error handling Slack webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Handle WhatsApp webhook events (via Twilio)
    """
    try:
        form_data = await request.form()
        data = dict(form_data)
        
        # Extract WhatsApp message data
        from_number = data.get('From', '')
        to_number = data.get('To', '')
        body = data.get('Body', '')
        message_sid = data.get('MessageSid', '')
        account_sid = data.get('AccountSid', '')
        
        if body and from_number:
            whatsapp_message = WhatsAppMessage(
                from_number=from_number,
                to_number=to_number,
                body=body,
                message_sid=message_sid,
                account_sid=account_sid
            )
            
            await _handle_whatsapp_message(whatsapp_message)
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Error handling WhatsApp webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


async def _handle_slack_message(event: dict):
    """Handle incoming Slack message"""
    try:
        user_id = event.get('user')
        channel_id = event.get('channel')
        text = event.get('text', '')
        thread_ts = event.get('thread_ts')
        
        if not text or not user_id:
            return
        
        # Create chat message
        chat_message = ChatMessage(
            message=text,
            user_id=f"slack_{user_id}",
            session_id=f"slack_{channel_id}_{thread_ts or event.get('ts')}",
            channel=Channel.SLACK,
            metadata={
                "slack_channel": channel_id,
                "slack_user": user_id,
                "thread_ts": thread_ts,
                "ts": event.get('ts')
            }
        )
        
        # Process message with chatbot
        response = await chatbot_service.process_message(chat_message)
        
        # Send response back to Slack
        await _send_slack_message(channel_id, response.response, thread_ts)
        
    except Exception as e:
        logger.error(f"Error handling Slack message: {e}")


async def _handle_whatsapp_message(whatsapp_message: WhatsAppMessage):
    """Handle incoming WhatsApp message"""
    try:
        # Extract phone number without country code prefix
        user_id = whatsapp_message.from_number.replace('+', '').replace('whatsapp:', '')
        
        # Create chat message
        chat_message = ChatMessage(
            message=whatsapp_message.body,
            user_id=f"whatsapp_{user_id}",
            session_id=f"whatsapp_{user_id}",
            channel=Channel.WHATSAPP,
            metadata={
                "from_number": whatsapp_message.from_number,
                "to_number": whatsapp_message.to_number,
                "message_sid": whatsapp_message.message_sid
            }
        )
        
        # Process message with chatbot
        response = await chatbot_service.process_message(chat_message)
        
        # Send response back via WhatsApp
        await _send_whatsapp_message(whatsapp_message.from_number, response.response)
        
    except Exception as e:
        logger.error(f"Error handling WhatsApp message: {e}")


async def _send_slack_message(channel: str, text: str, thread_ts: Optional[str] = None):
    """Send message to Slack"""
    try:
        if not settings.slack_bot_token:
            logger.warning("Slack bot token not configured")
            return
        
        from slack_sdk.web.async_client import AsyncWebClient
        
        client = AsyncWebClient(token=settings.slack_bot_token)
        
        await client.chat_postMessage(
            channel=channel,
            text=text,
            thread_ts=thread_ts
        )
        
        logger.info(f"Sent message to Slack channel {channel}")
        
    except Exception as e:
        logger.error(f"Error sending Slack message: {e}")


async def _send_whatsapp_message(to_number: str, message: str):
    """Send message via WhatsApp (Twilio)"""
    try:
        if not all([settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_phone_number]):
            logger.warning("Twilio credentials not configured")
            return
        
        from twilio.rest import Client
        
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        
        message = client.messages.create(
            body=message,
            from_=f'whatsapp:{settings.twilio_phone_number}',
            to=to_number
        )
        
        logger.info(f"Sent WhatsApp message {message.sid}")
        
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")


def _verify_slack_signature(body: bytes, signature: str, timestamp: str) -> bool:
    """Verify Slack request signature"""
    try:
        if not settings.slack_signing_secret:
            return False
        
        # Create the signature
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        my_signature = 'v0=' + hmac.new(
            settings.slack_signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(my_signature, signature)
    
    except Exception as e:
        logger.error(f"Error verifying Slack signature: {e}")
        return False
