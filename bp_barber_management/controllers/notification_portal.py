# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied, ValidationError
import logging

_logger = logging.getLogger(__name__)


class BarberNotificationPortalController(http.Controller):
    """Controller for tokenized appointment confirmation/cancellation links"""

    def _validate_appointment_token(self, name, token):
        """
        Validate appointment by name and token
        
        Args:
            name: Appointment name/number
            token: Appointment token
            
        Returns:
            appointment record or None if invalid
        """
        try:
            appointment = request.env['bp.barber.appointment'].sudo().search([
                ('name', '=', name),
                ('appointment_token', '=', token)
            ], limit=1)
            
            return appointment if appointment.exists() else None
            
        except Exception as e:
            _logger.error(f"Error validating appointment token: {e}")
            return None

    @http.route('/barber/apt/<string:name>/<string:token>/confirm', 
                type='http', auth='public', website=True)
    def appointment_confirm(self, name, token, **kwargs):
        """
        Confirm appointment via tokenized link
        
        Args:
            name: Appointment name/number
            token: Appointment token
        """
        try:
            appointment = self._validate_appointment_token(name, token)
            
            if not appointment:
                return request.render('bp_barber_management.appt_error_page', {
                    'error_title': 'Invalid Link',
                    'error_message': 'This confirmation link is invalid or has expired.',
                })
            
            # Confirm appointment if valid state
            if appointment.state in ['draft', 'confirmed']:
                if appointment.state == 'draft':
                    appointment.state = 'confirmed'
                    
                appointment.message_post(
                    body='Appointment confirmed via email link by customer.',
                    message_type='comment'
                )
                
                return request.render('bp_barber_management.appt_confirmed_page', {
                    'appointment': appointment,
                    'company': appointment.company_id,
                })
            else:
                return request.render('bp_barber_management.appt_error_page', {
                    'error_title': 'Cannot Confirm',
                    'error_message': f'This appointment is already {appointment.state} and cannot be confirmed.',
                    'appointment': appointment,
                })
                
        except Exception as e:
            _logger.error(f"Error in appointment confirm: {e}")
            return request.render('bp_barber_management.appt_error_page', {
                'error_title': 'System Error',
                'error_message': 'An error occurred while processing your request. Please try again or contact us directly.',
            })

    @http.route('/barber/apt/<string:name>/<string:token>/cancel', 
                type='http', auth='public', website=True)
    def appointment_cancel(self, name, token, **kwargs):
        """
        Cancel appointment via tokenized link
        
        Args:
            name: Appointment name/number
            token: Appointment token
        """
        try:
            appointment = self._validate_appointment_token(name, token)
            
            if not appointment:
                return request.render('bp_barber_management.appt_error_page', {
                    'error_title': 'Invalid Link',
                    'error_message': 'This cancellation link is invalid or has expired.',
                })
            
            # Cancel appointment if valid state
            if appointment.state in ['draft', 'confirmed']:
                old_state = appointment.state
                appointment.state = 'cancelled'
                
                appointment.message_post(
                    body=f'Appointment cancelled via email link by customer (was {old_state}).',
                    message_type='comment'
                )
                
                # Create follow-up activity
                try:
                    manager_group = request.env.ref('bp_barber_management.group_bp_barber_manager')
                    if manager_group and manager_group.users:
                        manager_user = manager_group.users[0]
                    else:
                        manager_user = request.env.ref('base.user_admin')
                        
                    appointment.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=f'Customer cancelled appointment: {appointment.partner_id.name if appointment.partner_id else "Unknown"}',
                        note=f'Customer cancelled appointment {appointment.name} via email link. Consider following up or rebooking.',
                        user_id=manager_user.id,
                        date_deadline=appointment.start_datetime.date() if appointment.start_datetime else None
                    )
                except Exception as activity_error:
                    _logger.warning(f"Could not create activity for cancelled appointment: {activity_error}")
                
                # Send cancellation confirmation email if settings allow
                try:
                    notification_service = request.env['bp.barber.notification.service'].sudo()
                    settings = notification_service.get_notification_settings()
                    
                    if (settings.get('notify_on_confirm') and 
                        appointment.partner_id and 
                        appointment.partner_id.email and 
                        not appointment.email_opt_out):
                        
                        appointment._send_mail_template('bp_barber_management.mail_tmpl_appt_cancelled')
                except Exception as email_error:
                    _logger.warning(f"Could not send cancellation email: {email_error}")
                
                return request.render('bp_barber_management.appt_cancelled_page', {
                    'appointment': appointment,
                    'company': appointment.company_id,
                })
            else:
                return request.render('bp_barber_management.appt_error_page', {
                    'error_title': 'Cannot Cancel',
                    'error_message': f'This appointment is {appointment.state} and cannot be cancelled.',
                    'appointment': appointment,
                })
                
        except Exception as e:
            _logger.error(f"Error in appointment cancel: {e}")
            return request.render('bp_barber_management.appt_error_page', {
                'error_title': 'System Error',
                'error_message': 'An error occurred while processing your request. Please try again or contact us directly.',
            })

    @http.route('/barber/apt/test', type='http', auth='public')
    def portal_test(self, **kwargs):
        """Test endpoint for notification portal"""
        return """
        <html>
            <head><title>Notification Portal Test</title></head>
            <body>
                <h1>Barber Notification Portal</h1>
                <p>Portal controller is working!</p>
                <p>Use tokenized links to confirm/cancel appointments:</p>
                <ul>
                    <li>/barber/apt/&lt;appointment_name&gt;/&lt;token&gt;/confirm</li>
                    <li>/barber/apt/&lt;appointment_name&gt;/&lt;token&gt;/cancel</li>
                </ul>
            </body>
        </html>
        """