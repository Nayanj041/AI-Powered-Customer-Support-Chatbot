from simple_salesforce import Salesforce
import asyncio
from typing import Optional, List, Dict, Any
from ..models.schemas import SalesforceContact, SalesforceCase, SalesforceOrder
from ..core.config import settings
from ..core.cache import cache_manager
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SalesforceService:
    def __init__(self):
        self.sf: Optional[Salesforce] = None
        self.is_connected = False
    
    async def connect(self):
        """Connect to Salesforce"""
        try:
            if not all([
                settings.salesforce_username,
                settings.salesforce_password,
                settings.salesforce_security_token
            ]):
                logger.warning("Salesforce credentials not configured")
                return False
            
            # Run Salesforce connection in thread pool since it's synchronous
            loop = asyncio.get_event_loop()
            self.sf = await loop.run_in_executor(
                None,
                self._create_salesforce_connection
            )
            
            self.is_connected = True
            logger.info("Successfully connected to Salesforce")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Salesforce: {e}")
            self.is_connected = False
            return False
    
    def _create_salesforce_connection(self) -> Salesforce:
        """Create Salesforce connection (synchronous)"""
        return Salesforce(
            username=settings.salesforce_username,
            password=settings.salesforce_password,
            security_token=settings.salesforce_security_token,
            domain=settings.salesforce_domain
        )
    
    async def get_contact_by_email(self, email: str) -> Optional[SalesforceContact]:
        """Get contact information by email"""
        if not self.is_connected:
            await self.connect()
        
        if not self.sf:
            return None
        
        try:
            # Check cache first
            cached_contact = await cache_manager.get_salesforce_data(f"contact_email:{email}")
            if cached_contact:
                return SalesforceContact(**cached_contact)
            
            # Query Salesforce
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._query_contact_by_email,
                email
            )
            
            if result and result['totalSize'] > 0:
                contact_data = result['records'][0]
                contact = SalesforceContact(
                    id=contact_data['Id'],
                    name=contact_data.get('Name', ''),
                    email=contact_data.get('Email'),
                    phone=contact_data.get('Phone'),
                    account_id=contact_data.get('AccountId'),
                    last_activity_date=self._parse_date(contact_data.get('LastActivityDate'))
                )
                
                # Cache the result
                await cache_manager.cache_salesforce_data(
                    f"contact_email:{email}",
                    contact.dict(),
                    ttl=600
                )
                
                return contact
            
            return None
            
        except Exception as e:
            logger.error(f"Error querying contact by email {email}: {e}")
            return None
    
    def _query_contact_by_email(self, email: str):
        """Query contact by email (synchronous)"""
        return self.sf.query(f"""
            SELECT Id, Name, Email, Phone, AccountId, LastActivityDate
            FROM Contact 
            WHERE Email = '{email}'
            LIMIT 1
        """)
    
    async def get_contact_cases(self, contact_id: str) -> List[SalesforceCase]:
        """Get cases for a contact"""
        if not self.is_connected:
            await self.connect()
        
        if not self.sf:
            return []
        
        try:
            # Check cache first
            cache_key = f"contact_cases:{contact_id}"
            cached_cases = await cache_manager.get_salesforce_data(cache_key)
            if cached_cases:
                return [SalesforceCase(**case) for case in cached_cases]
            
            # Query Salesforce
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._query_contact_cases,
                contact_id
            )
            
            cases = []
            if result and result['totalSize'] > 0:
                for case_data in result['records']:
                    case = SalesforceCase(
                        id=case_data['Id'],
                        case_number=case_data['CaseNumber'],
                        subject=case_data.get('Subject', ''),
                        description=case_data.get('Description'),
                        status=case_data.get('Status', ''),
                        priority=case_data.get('Priority', ''),
                        contact_id=case_data.get('ContactId'),
                        account_id=case_data.get('AccountId'),
                        created_date=self._parse_date(case_data['CreatedDate']),
                        last_modified_date=self._parse_date(case_data['LastModifiedDate'])
                    )
                    cases.append(case)
                
                # Cache the results
                cases_dict = [case.dict() for case in cases]
                await cache_manager.cache_salesforce_data(cache_key, cases_dict, ttl=300)
            
            return cases
            
        except Exception as e:
            logger.error(f"Error querying cases for contact {contact_id}: {e}")
            return []
    
    def _query_contact_cases(self, contact_id: str):
        """Query cases for contact (synchronous)"""
        return self.sf.query(f"""
            SELECT Id, CaseNumber, Subject, Description, Status, Priority, 
                   ContactId, AccountId, CreatedDate, LastModifiedDate
            FROM Case 
            WHERE ContactId = '{contact_id}'
            ORDER BY CreatedDate DESC
            LIMIT 10
        """)
    
    async def get_contact_orders(self, contact_id: str) -> List[SalesforceOrder]:
        """Get orders for a contact"""
        if not self.is_connected:
            await self.connect()
        
        if not self.sf:
            return []
        
        try:
            # Check cache first
            cache_key = f"contact_orders:{contact_id}"
            cached_orders = await cache_manager.get_salesforce_data(cache_key)
            if cached_orders:
                return [SalesforceOrder(**order) for order in cached_orders]
            
            # Query Salesforce
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._query_contact_orders,
                contact_id
            )
            
            orders = []
            if result and result['totalSize'] > 0:
                for order_data in result['records']:
                    order = SalesforceOrder(
                        id=order_data['Id'],
                        order_number=order_data.get('OrderNumber', ''),
                        account_id=order_data.get('AccountId', ''),
                        contact_id=order_data.get('BillToContactId'),
                        status=order_data.get('Status', ''),
                        total_amount=order_data.get('TotalAmount'),
                        order_date=self._parse_date(order_data.get('EffectiveDate')),
                        items=[]  # Would need separate query for order items
                    )
                    orders.append(order)
                
                # Cache the results
                orders_dict = [order.dict() for order in orders]
                await cache_manager.cache_salesforce_data(cache_key, orders_dict, ttl=300)
            
            return orders
            
        except Exception as e:
            logger.error(f"Error querying orders for contact {contact_id}: {e}")
            return []
    
    def _query_contact_orders(self, contact_id: str):
        """Query orders for contact (synchronous)"""
        return self.sf.query(f"""
            SELECT Id, OrderNumber, AccountId, BillToContactId, Status, 
                   TotalAmount, EffectiveDate
            FROM Order 
            WHERE BillToContactId = '{contact_id}'
            ORDER BY EffectiveDate DESC
            LIMIT 10
        """)
    
    async def create_case(
        self, 
        contact_id: str, 
        subject: str, 
        description: str,
        priority: str = "Medium"
    ) -> Optional[str]:
        """Create a new case in Salesforce"""
        if not self.is_connected:
            await self.connect()
        
        if not self.sf:
            return None
        
        try:
            case_data = {
                'ContactId': contact_id,
                'Subject': subject,
                'Description': description,
                'Priority': priority,
                'Status': 'New',
                'Origin': 'Chatbot'
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.sf.Case.create,
                case_data
            )
            
            case_id = result.get('id')
            if case_id:
                logger.info(f"Created case {case_id} for contact {contact_id}")
                # Invalidate cache for contact cases
                await cache_manager.delete(f"contact_cases:{contact_id}")
            
            return case_id
            
        except Exception as e:
            logger.error(f"Error creating case: {e}")
            return None
    
    async def search_knowledge_articles(self, query: str) -> List[Dict[str, Any]]:
        """Search knowledge articles for relevant information"""
        if not self.is_connected:
            await self.connect()
        
        if not self.sf:
            return []
        
        try:
            # This would depend on your Salesforce knowledge base setup
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Error searching knowledge articles: {e}")
            return []
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse Salesforce date string"""
        if not date_str:
            return None
        
        try:
            # Salesforce returns dates in ISO format
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None
    
    async def get_customer_summary(self, email: str) -> Dict[str, Any]:
        """Get comprehensive customer summary"""
        contact = await self.get_contact_by_email(email)
        if not contact:
            return {}
        
        # Get cases and orders in parallel
        cases_task = self.get_contact_cases(contact.id)
        orders_task = self.get_contact_orders(contact.id)
        
        cases, orders = await asyncio.gather(cases_task, orders_task)
        
        # Calculate some metrics
        open_cases = [case for case in cases if case.status not in ['Closed', 'Resolved']]
        recent_orders = [
            order for order in orders 
            if order.order_date and order.order_date > datetime.now() - timedelta(days=90)
        ]
        
        return {
            'contact': contact.dict() if contact else None,
            'open_cases': len(open_cases),
            'recent_cases': len([case for case in cases if case.created_date > datetime.now() - timedelta(days=30)]),
            'recent_orders': len(recent_orders),
            'total_orders': len(orders),
            'last_order_date': max([order.order_date for order in orders]) if orders else None,
            'customer_tier': 'Premium' if len(orders) > 5 else 'Standard'  # Simple tier logic
        }


# Global Salesforce service instance
salesforce_service = SalesforceService()
