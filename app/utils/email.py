# ================================
# AWS SES EMAIL SERVICE (utils/email.py)
# ================================

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import List, Optional, Dict, Any
import logging
import smtplib
from app.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """AWS SES Email Service mit SMTP Fallback"""
    
    def __init__(self):
        self.ses_client = None
        self.template_env = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialisiert AWS SES Client und Template Engine"""
        try:
            # AWS SES Client
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                self.ses_client = boto3.client(
                    'ses',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                logger.info("AWS SES client initialized successfully")
            else:
                logger.warning("AWS credentials not provided, SES will not be available")
            
            # Jinja2 Template Engine für Email Templates
            self.template_env = Environment(
                loader=FileSystemLoader(settings.EMAIL_TEMPLATES_DIR),
                autoescape=select_autoescape(['html', 'xml'])
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize email service: {e}")
    
    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        template_name: str,
        template_data: Dict[str, Any],
        from_email: str = None,
        from_name: str = None,
        reply_to: str = None,
        cc_emails: List[str] = None,
        bcc_emails: List[str] = None
    ) -> bool:
        """Sendet Email über AWS SES mit Template"""
        
        try:
            # Template rendern
            html_content = await self._render_template(f"{template_name}.html", template_data)
            text_content = await self._render_template(f"{template_name}.txt", template_data)
            
            # Email-Adresse Formatierung
            from_address = self._format_email_address(
                from_email or settings.AWS_SES_FROM_EMAIL,
                from_name or settings.AWS_SES_FROM_NAME
            )
            
            # AWS SES Versand versuchen
            if self.ses_client:
                success = await self._send_via_ses(
                    to_emails, subject, html_content, text_content,
                    from_address, reply_to, cc_emails, bcc_emails
                )
                if success:
                    return True
                    
            # Fallback zu SMTP
            logger.warning("SES failed, attempting SMTP fallback")
            return await self._send_via_smtp(
                to_emails, subject, html_content, text_content,
                from_address, reply_to, cc_emails, bcc_emails
            )
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False
    
    async def _send_via_ses(
        self, 
        to_emails: List[str], 
        subject: str, 
        html_content: str, 
        text_content: str,
        from_address: str,
        reply_to: str = None,
        cc_emails: List[str] = None,
        bcc_emails: List[str] = None
    ) -> bool:
        """Sendet Email über AWS SES"""
        
        try:
            # Destination aufbauen
            destination = {'ToAddresses': to_emails}
            if cc_emails:
                destination['CcAddresses'] = cc_emails
            if bcc_emails:
                destination['BccAddresses'] = bcc_emails
            
            # Message aufbauen
            message = {
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Html': {'Data': html_content, 'Charset': 'UTF-8'},
                    'Text': {'Data': text_content, 'Charset': 'UTF-8'}
                }
            }
            
            # SES Send-Parameter
            send_params = {
                'Source': from_address,
                'Destination': destination,
                'Message': message
            }
            
            # Reply-To Header
            if reply_to:
                send_params['ReplyToAddresses'] = [reply_to]
            
            # Configuration Set für Tracking
            if settings.AWS_SES_CONFIGURATION_SET:
                send_params['ConfigurationSetName'] = settings.AWS_SES_CONFIGURATION_SET
            
            # Email senden
            response = self.ses_client.send_email(**send_params)
            
            logger.info(f"Email sent via SES. MessageId: {response['MessageId']}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"SES sending failed: {error_code} - {e.response['Error']['Message']}")
            return False
        except Exception as e:
            logger.error(f"SES sending failed: {e}")
            return False
    
    async def _send_via_smtp(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: str,
        from_address: str,
        reply_to: str = None,
        cc_emails: List[str] = None,
        bcc_emails: List[str] = None
    ) -> bool:
        """Fallback SMTP-Versand"""
        
        if not settings.SMTP_HOST:
            logger.error("No SMTP configuration available")
            return False
        
        try:
            # MIME Message erstellen
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_address
            msg['To'] = ', '.join(to_emails)
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # Text und HTML Teile hinzufügen
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # SMTP Versand
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                
                all_recipients = to_emails + (cc_emails or []) + (bcc_emails or [])
                server.send_message(msg, to_addrs=all_recipients)
            
            logger.info("Email sent via SMTP fallback")
            return True
            
        except Exception as e:
            logger.error(f"SMTP sending failed: {e}")
            return False
    
    async def _render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """Rendert Jinja2 Template"""
        try:
            template = self.template_env.get_template(template_name)
            return template.render(**data)
        except Exception as e:
            logger.error(f"Template rendering failed for {template_name}: {e}")
            return ""
    
    def _format_email_address(self, email: str, name: str = None) -> str:
        """Formatiert Email-Adresse mit optionalem Display-Namen"""
        if name:
            return f"{name} <{email}>"
        return email
    
    # ================================
    # Vordefinierte Email-Templates
    # ================================
    
    async def send_welcome_email(
        self, 
        to_email: str, 
        user_name: str, 
        temp_password: str = None,
        verification_token: str = None,
        tenant_name: str = None
    ) -> bool:
        """Sendet Welcome-Email an neuen User"""
        
        template_data = {
            'user_name': user_name,
            'tenant_name': tenant_name or 'Your Organization',
            'temp_password': temp_password,
            'verification_link': f"{settings.FRONTEND_URL}/verify-email?token={verification_token}" if verification_token else None,
            'login_url': f"{settings.FRONTEND_URL}/login",
            'app_name': settings.APP_NAME,
            'support_email': settings.AWS_SES_REPLY_TO or settings.AWS_SES_FROM_EMAIL
        }
        
        subject = f"Welcome to {settings.APP_NAME}"
        if tenant_name:
            subject += f" - {tenant_name}"
        
        return await self.send_email(
            to_emails=[to_email],
            subject=subject,
            template_name="welcome",
            template_data=template_data
        )
    
    async def send_password_reset_email(
        self, 
        to_email: str, 
        user_name: str, 
        reset_token: str
    ) -> bool:
        """Sendet Password-Reset-Email"""
        
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        template_data = {
            'user_name': user_name,
            'reset_link': reset_link,
            'app_name': settings.APP_NAME,
            'expires_hours': 24
        }
        
        return await self.send_email(
            to_emails=[to_email],
            subject=f"Password Reset - {settings.APP_NAME}",
            template_name="password_reset",
            template_data=template_data
        )
    
    async def send_email_verification(
        self, 
        to_email: str, 
        user_name: str, 
        verification_token: str
    ) -> bool:
        """Sendet Email-Verifizierungs-Email"""
        
        verification_link = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        
        template_data = {
            'user_name': user_name,
            'verification_link': verification_link,
            'app_name': settings.APP_NAME
        }
        
        return await self.send_email(
            to_emails=[to_email],
            subject=f"Verify Your Email - {settings.APP_NAME}",
            template_name="email_verification",
            template_data=template_data
        )
    
    async def send_security_alert(
        self, 
        to_email: str, 
        user_name: str, 
        event_type: str,
        ip_address: str = None,
        timestamp: str = None
    ) -> bool:
        """Sendet Sicherheits-Benachrichtigung"""
        
        template_data = {
            'user_name': user_name,
            'event_type': event_type,
            'ip_address': ip_address,
            'timestamp': timestamp,
            'app_name': settings.APP_NAME,
            'support_email': settings.AWS_SES_REPLY_TO or settings.AWS_SES_FROM_EMAIL
        }
        
        return await self.send_email(
            to_emails=[to_email],
            subject=f"Security Alert - {settings.APP_NAME}",
            template_name="security_alert",
            template_data=template_data
        )

# Singleton Instance
email_service = EmailService()