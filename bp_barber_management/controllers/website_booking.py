# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class WebsiteBooking(http.Controller):

    @http.route('/barber/booking', auth='public', website=True)
    def booking_page(self, **kwargs):
        """Main booking page"""
        # Check if online booking is enabled
        if not self._is_online_booking_enabled():
            return request.not_found()
        
        # Get active services and barbers
        services = request.env['bp.barber.service'].sudo().search([('active', '=', True)])
        barbers = request.env['bp.barber.barber'].sudo().search([('active', '=', True)])
        
        values = {
            'services': services,
            'barbers': barbers,
            'error': kwargs.get('error'),
            'form_data': kwargs
        }
        return request.render('bp_barber_management.booking_page', values)

    @http.route('/barber/booking/slots', auth='public', methods=['POST'], csrf=False, type='json')
    def get_available_slots(self, **kwargs):
        """Get available time slots for booking"""
        try:
            barber_id = int(kwargs.get('barber_id', 0))
            date_str = kwargs.get('date', '')
            service_ids = kwargs.get('service_ids', [])
            
            if not barber_id or not date_str or not service_ids:
                return {'error': 'Missing required parameters'}
            
            # Calculate total duration from services
            services = request.env['bp.barber.service'].sudo().browse(service_ids)
            total_duration = sum(services.mapped('duration_minutes'))
            
            if total_duration <= 0:
                return {'error': 'Invalid service selection'}
            
            # Get available slots
            slots = request.env['bp.barber.appointment'].sudo().get_available_slots(
                barber_id, date_str, total_duration
            )
            
            # Format slots for frontend
            formatted_slots = []
            for slot in slots:
                formatted_slots.append({
                    'start': slot['start'].strftime('%Y-%m-%d %H:%M:%S'),
                    'end': slot['end'].strftime('%Y-%m-%d %H:%M:%S'),
                    'display': slot['start'].strftime('%H:%M')
                })
            
            return {'slots': formatted_slots}
            
        except Exception as e:
            _logger.error("Error getting available slots: %s", str(e))
            return {'error': 'An error occurred while fetching available slots'}

    @http.route('/barber/booking/confirm', auth='public', methods=['POST'], csrf=True, website=True)
    def confirm_booking(self, **kwargs):
        """Confirm the booking and create appointment"""
        try:
            # Extract form data
            name = kwargs.get('name', '').strip()
            phone = kwargs.get('phone', '').strip()
            email = kwargs.get('email', '').strip()
            barber_id = int(kwargs.get('barber_id', 0))
            service_ids = [int(x) for x in kwargs.get('service_ids', '').split(',') if x.strip()]
            slot_start = kwargs.get('slot_start', '').strip()
            note = kwargs.get('note', '').strip()
            
            # Validate required fields
            if not phone:
                return self._booking_error('Phone number is required')
            if not barber_id:
                return self._booking_error('Please select a barber')
            if not service_ids:
                return self._booking_error('Please select at least one service')
            if not slot_start:
                return self._booking_error('Please select a time slot')
            
            # Parse slot start time
            try:
                start_datetime = datetime.strptime(slot_start, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return self._booking_error('Invalid time slot format')
            
            # Validate services and calculate duration
            services = request.env['bp.barber.service'].sudo().browse(service_ids)
            if not services:
                return self._booking_error('Invalid service selection')
            
            total_duration = sum(services.mapped('duration_minutes'))
            
            # Re-check slot availability to prevent conflicts
            available_slots = request.env['bp.barber.appointment'].sudo().get_available_slots(
                barber_id, start_datetime.strftime('%Y-%m-%d'), total_duration
            )
            
            # Check if the requested slot is still available
            slot_available = False
            for slot in available_slots:
                if slot['start'] == start_datetime:
                    slot_available = True
                    break
            
            if not slot_available:
                return self._booking_error(
                    'Sorry, the selected time slot is no longer available. Please choose another time.',
                    refresh_slots=True
                )
            
            # Find or create partner
            partner = None
            if email:
                partner = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
            if not partner and phone:
                partner = request.env['res.partner'].sudo().search([('phone', '=', phone)], limit=1)
            
            if not partner:
                # Create new partner
                partner_vals = {
                    'name': name or 'Website Customer',
                    'phone': phone,
                    'is_company': False
                }
                if email:
                    partner_vals['email'] = email
                
                partner = request.env['res.partner'].sudo().create(partner_vals)
            
            # Create appointment
            appointment_vals = {
                'partner_id': partner.id,
                'phone': phone,
                'email': email or '',
                'barber_id': barber_id,
                'service_ids': [(6, 0, service_ids)],
                'start_datetime': start_datetime,
                'state': 'confirmed',
                'note': note
            }
            
            try:
                appointment = request.env['bp.barber.appointment'].sudo().create(appointment_vals)
                _logger.info(f"Website booking: Appointment created successfully: {appointment.name} (ID: {appointment.id})")
                
                # Redirect to thank you page
                return request.redirect(f'/barber/booking/thanks?apt={appointment.name}')
            except Exception as e:
                _logger.error(f"Website booking: Failed to create appointment: {str(e)}")
                _logger.error(f"Website booking: Appointment values: {appointment_vals}")
                return self._booking_error(f'Failed to create appointment: {str(e)}')
            
        except Exception as e:
            _logger.error("Error confirming booking: %s", str(e))
            return self._booking_error('An error occurred while processing your booking. Please try again.')

    @http.route('/barber/booking/thanks', auth='public', website=True)
    def booking_thanks(self, **kwargs):
        """Thank you page after successful booking"""
        apt_name = kwargs.get('apt')
        
        appointment = None
        if apt_name:
            appointment = request.env['bp.barber.appointment'].sudo().search([
                ('name', '=', apt_name)
            ], limit=1)
            _logger.info(f"Website booking thanks: Looking for appointment '{apt_name}', found: {appointment.id if appointment else 'None'}")
        
        if not appointment:
            _logger.warning(f"Website booking thanks: Appointment '{apt_name}' not found, redirecting to booking page")
            return request.redirect('/barber/booking')
        
        values = {
            'appointment': appointment
        }
        return request.render('bp_barber_management.booking_thanks', values)

    def _is_online_booking_enabled(self):
        """Check if online booking is enabled"""
        param = request.env['ir.config_parameter'].sudo().get_param(
            'bp_barber.allow_online_booking', 'True'
        )
        return param.lower() != 'false'

    def _booking_error(self, error_message, refresh_slots=False):
        """Return to booking page with error message"""
        kwargs = dict(request.httprequest.form)
        kwargs['error'] = error_message
        if refresh_slots:
            kwargs['refresh_slots'] = True
        return self.booking_page(**kwargs)