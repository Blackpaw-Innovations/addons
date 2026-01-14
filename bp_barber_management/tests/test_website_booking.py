# -*- coding: utf-8 -*-

from odoo.tests.common import HttpCase
from odoo.tests import tagged
from datetime import datetime, timedelta
import json


@tagged('post_install', '-at_install')
class TestWebsiteBooking(HttpCase):
    """Test website booking functionality"""
    
    def setUp(self):
        super().setUp()
        
        # Create test data
        self.company = self.env.company
        
        # Create test service
        self.service = self.env['bp.barber.service'].create({
            'name': 'Test Website Cut',
            'code': 'TWCUT',
            'duration_minutes': 30,
            'list_price': 25.00,
        })
        
        # Create test chair
        self.chair = self.env['bp.barber.chair'].create({
            'name': 'Test Website Chair',
            'code': 'TWC1',
        })
        
        # Create test barber
        self.barber = self.env['bp.barber.barber'].create({
            'name': 'Test Website Barber',
            'barber_code': 'TWB1',
            'chair_id': self.chair.id,
        })
        
        # Create schedule for the barber (Monday to Friday, 9-17)
        for weekday in range(5):  # Monday to Friday
            self.env['bp.barber.schedule'].create({
                'barber_id': self.barber.id,
                'weekday': str(weekday),
                'start_time': 9.0,
                'end_time': 17.0,
            })
    
    def test_booking_page_loads(self):
        """Test that the booking page loads correctly"""
        # Enable online booking
        self.env['ir.config_parameter'].sudo().set_param('bp_barber.allow_online_booking', 'True')
        
        # Test GET request to booking page
        response = self.url_open('/barber/booking')
        
        # Should return 200 and contain booking form
        self.assertEqual(response.status_code, 200)
        self.assertIn('Book an Appointment', response.text)
        self.assertIn('booking-form', response.text)
    
    def test_slots_available_for_scheduled_barber(self):
        """Test that slots are available for a barber with schedule"""
        # Get next Monday (weekday 0)
        today = datetime.now().date()
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        next_monday = today + timedelta(days_ahead)
        
        # Make JSON request to get slots
        data = {
            'barber_id': self.barber.id,
            'date': next_monday.strftime('%Y-%m-%d'),
            'service_ids': [self.service.id]
        }
        
        response = self.url_open('/barber/booking/slots', 
                                data=json.dumps(data),
                                headers={'Content-Type': 'application/json'})
        
        self.assertEqual(response.status_code, 200)
        
        result = response.json()
        self.assertIn('slots', result)
        self.assertGreater(len(result['slots']), 0, "Should have available slots for scheduled barber")
    
    def test_confirm_creates_confirmed_appointment(self):
        """Test that confirming a booking creates a confirmed appointment"""
        # Get next Monday
        today = datetime.now().date()
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_monday = today + timedelta(days_ahead)
        
        # Get available slots first
        slots = self.env['bp.barber.appointment'].get_available_slots(
            self.barber.id,
            next_monday.strftime('%Y-%m-%d'),
            self.service.duration_minutes
        )
        
        self.assertTrue(slots, "Should have available slots")
        
        # Use the first available slot
        first_slot = slots[0]
        
        # Prepare booking data
        booking_data = {
            'name': 'John Website Customer',
            'phone': '+1-555-9999',
            'email': 'john.website@example.com',
            'barber_id': str(self.barber.id),
            'service_ids': str(self.service.id),
            'slot_start': first_slot['start'].strftime('%Y-%m-%d %H:%M:%S'),
            'note': 'Test booking from website'
        }
        
        # Submit booking
        response = self.url_open('/barber/booking/confirm', data=booking_data)
        
        # Should redirect to thank you page
        self.assertEqual(response.status_code, 200)
        
        # Check that appointment was created
        appointment = self.env['bp.barber.appointment'].search([
            ('barber_id', '=', self.barber.id),
            ('start_datetime', '=', first_slot['start']),
            ('state', '=', 'confirmed')
        ])
        
        self.assertTrue(appointment, "Confirmed appointment should be created")
        self.assertEqual(appointment.partner_id.email, 'john.website@example.com')
        self.assertEqual(appointment.phone, '+1-555-9999')
        self.assertIn(self.service, appointment.service_ids)
    
    def test_conflict_prevented(self):
        """Test that booking conflicts are prevented"""
        # Get next Monday
        today = datetime.now().date()
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_monday = today + timedelta(days_ahead)
        
        # Create an existing appointment at 10:00
        existing_start = datetime.combine(next_monday, datetime.min.time().replace(hour=10, minute=0))
        existing_appointment = self.env['bp.barber.appointment'].create({
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': existing_start,
            'state': 'confirmed',
            'phone': '+1-555-1111'
        })
        
        # Try to book the same time slot
        booking_data = {
            'name': 'Jane Conflict Customer',
            'phone': '+1-555-8888',
            'barber_id': str(self.barber.id),
            'service_ids': str(self.service.id),
            'slot_start': existing_start.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Submit conflicting booking
        response = self.url_open('/barber/booking/confirm', data=booking_data)
        
        # Should return to booking page with error
        self.assertEqual(response.status_code, 200)
        self.assertIn('no longer available', response.text)
        
        # Verify no duplicate appointment was created
        conflicting_appointments = self.env['bp.barber.appointment'].search([
            ('barber_id', '=', self.barber.id),
            ('start_datetime', '=', existing_start),
            ('phone', '=', '+1-555-8888')
        ])
        
        self.assertFalse(conflicting_appointments, "Conflicting appointment should not be created")
    
    def test_schedule_model_constraints(self):
        """Test schedule model validation"""
        from odoo.exceptions import ValidationError
        
        # Test invalid time range (end before start)
        with self.assertRaises(ValidationError):
            self.env['bp.barber.schedule'].create({
                'barber_id': self.barber.id,
                'weekday': '0',
                'start_time': 17.0,
                'end_time': 9.0,  # End before start
            })
        
        # Test duplicate schedule for same barber and weekday
        from psycopg2 import IntegrityError
        
        # First schedule should work
        schedule1 = self.env['bp.barber.schedule'].create({
            'barber_id': self.barber.id,
            'weekday': '6',  # Sunday
            'start_time': 10.0,
            'end_time': 16.0,
        })
        
        # Duplicate should fail
        with self.assertRaises((ValidationError, IntegrityError)):
            self.env['bp.barber.schedule'].create({
                'barber_id': self.barber.id,
                'weekday': '6',  # Same weekday
                'start_time': 11.0,
                'end_time': 17.0,
            })
    
    def test_slot_engine_respects_schedule(self):
        """Test that slot engine respects barber schedules"""
        # Get a Sunday (weekday 6) - barber should have no schedule for Sunday
        today = datetime.now().date()
        days_ahead = 6 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_sunday = today + timedelta(days_ahead)
        
        # Try to get slots for Sunday (no schedule)
        slots = self.env['bp.barber.appointment'].get_available_slots(
            self.barber.id,
            next_sunday.strftime('%Y-%m-%d'),
            30
        )
        
        self.assertEqual(len(slots), 0, "Should have no slots for days without schedule")
        
        # Get slots for Monday (has schedule)
        next_monday = next_sunday + timedelta(days=1)
        slots_monday = self.env['bp.barber.appointment'].get_available_slots(
            self.barber.id,
            next_monday.strftime('%Y-%m-%d'),
            30
        )
        
        self.assertGreater(len(slots_monday), 0, "Should have slots for scheduled days")
    
    def test_online_booking_disabled(self):
        """Test that booking page returns 404 when disabled"""
        # Disable online booking
        self.env['ir.config_parameter'].sudo().set_param('bp_barber.allow_online_booking', 'False')
        
        # Test GET request to booking page
        response = self.url_open('/barber/booking')
        
        # Should return 404
        self.assertEqual(response.status_code, 404)