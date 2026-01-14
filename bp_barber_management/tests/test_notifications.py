# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, HttpCase
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import uuid
import logging

_logger = logging.getLogger(__name__)


class TestBarberNotifications(TransactionCase):
    """Test notification system for barber appointments"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env['res.company'].browse(1)  # Use main company
        
        # Create test partner with email
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@customer.com',
            'phone': '123-456-7890',
        })
        
        # Create test barber
        cls.barber = cls.env['bp.barber.barber'].create({
            'name': 'Test Barber',
            'phone': '123-456-7890',
            'email': 'testbarber@example.com'
        })
        
        # Create test service
        cls.service = cls.env['bp.barber.service'].create({
            'name': 'Test Haircut',
            'list_price': 25.00,
            'duration_minutes': 30
        })
        
        # Enable notifications
        cls.env['ir.config_parameter'].sudo().set_param(
            'bp_barber_management.notify_on_confirm', 'True'
        )
        cls.env['ir.config_parameter'].sudo().set_param(
            'bp_barber_management.notify_reminder_enabled', 'True'
        )
        cls.env['ir.config_parameter'].sudo().set_param(
            'bp_barber_management.notify_followup_noshow', 'True'
        )

    def test_notification_settings_validation(self):
        """Test notification settings validation"""
        # Test valid settings
        settings = self.env['res.config.settings'].create({
            'bp_barber_notify_reminder_hours_primary': 24,
            'bp_barber_notify_reminder_hours_secondary': 2
        })
        settings._check_reminder_hours()  # Should not raise
        
        # Test invalid primary hours
        with self.assertRaises(ValidationError):
            invalid_settings = self.env['res.config.settings'].create({
                'bp_barber_notify_reminder_hours_primary': 0
            })
            invalid_settings._check_reminder_hours()
            
        # Test secondary >= primary
        with self.assertRaises(ValidationError):
            invalid_settings = self.env['res.config.settings'].create({
                'bp_barber_notify_reminder_hours_primary': 2,
                'bp_barber_notify_reminder_hours_secondary': 24
            })
            invalid_settings._check_reminder_hours()

    def test_appointment_token_generation(self):
        """Test that appointment tokens are generated on create"""
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() + timedelta(hours=24),
        })
        
        # Token should be generated automatically
        self.assertTrue(appointment.appointment_token)
        self.assertEqual(len(appointment.appointment_token), 32)  # UUID4 hex length
        
        # Token should be unique
        appointment2 = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() + timedelta(hours=25),
        })
        
        self.assertNotEqual(appointment.appointment_token, appointment2.appointment_token)

    def test_ics_generation(self):
        """Test ICS calendar file generation"""
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime(2025, 12, 25, 10, 0, 0),
            'duration_minutes': 30,
        })
        
        ics_content = appointment._build_ics_payload()
        self.assertIsNotNone(ics_content)
        
        # Check ICS format
        ics_str = ics_content.decode('utf-8')
        self.assertIn('BEGIN:VCALENDAR', ics_str)
        self.assertIn('BEGIN:VEVENT', ics_str)
        self.assertIn('SUMMARY:Barber Appointment: Test Haircut', ics_str)
        self.assertIn('DTSTART:20251225T100000Z', ics_str)
        self.assertIn('DTEND:20251225T103000Z', ics_str)
        self.assertIn(f'UID:{appointment.appointment_token}', ics_str)

    def test_confirm_sends_email(self):
        """Test that confirming appointment sends email"""
        # Count existing mails
        initial_mail_count = self.env['mail.mail'].search_count([])
        
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() + timedelta(hours=24),
        })
        
        # Confirm appointment
        appointment.action_confirm()
        
        # Check that email was queued (we can't easily test actual sending in tests)
        # Instead, check that a mail message was created
        messages = appointment.message_ids.filtered(lambda m: 'Email sent' in (m.body or ''))
        self.assertTrue(len(messages) > 0, "Confirmation email should be logged")

    def test_email_opt_out_respected(self):
        """Test that email opt-out is respected"""
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() + timedelta(hours=24),
            'email_opt_out': True,
        })
        
        # Confirm appointment
        appointment.action_confirm()
        
        # Check that email was skipped
        messages = appointment.message_ids.filtered(lambda m: 'Email notification skipped' in (m.body or ''))
        self.assertTrue(len(messages) > 0, "Email should be skipped for opted-out customers")

    def test_cron_sends_primary_reminder(self):
        """Test cron job sends primary reminders"""
        # Create appointment 24 hours from now (within primary reminder window)
        primary_hours = 24
        start_time = datetime.utcnow() + timedelta(hours=primary_hours)
        
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': start_time,
            'state': 'confirmed',
        })
        
        # Ensure reminder not sent yet
        self.assertFalse(appointment.reminder_primary_sent)
        
        # Run cron
        self.env['bp.barber.appointment'].cron_send_reminders()
        
        # Check that reminder was sent
        appointment.refresh()
        self.assertTrue(appointment.reminder_primary_sent)

    def test_cron_sends_secondary_reminder(self):
        """Test cron job sends secondary reminders"""
        # Set secondary reminder hours
        self.env['ir.config_parameter'].sudo().set_param(
            'bp_barber_management.notify_reminder_hours_secondary', '2'
        )
        
        # Create appointment 2 hours from now (within secondary reminder window)
        secondary_hours = 2
        start_time = datetime.utcnow() + timedelta(hours=secondary_hours)
        
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': start_time,
            'state': 'confirmed',
            'reminder_primary_sent': True,  # Primary already sent
        })
        
        # Ensure secondary reminder not sent yet
        self.assertFalse(appointment.reminder_secondary_sent)
        
        # Run cron
        self.env['bp.barber.appointment'].cron_send_reminders()
        
        # Check that secondary reminder was sent
        appointment.refresh()
        self.assertTrue(appointment.reminder_secondary_sent)

    def test_no_show_triggers_followup(self):
        """Test no-show triggers follow-up email and activity"""
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() - timedelta(hours=1),  # Past appointment
            'state': 'confirmed',
        })
        
        # Count activities before
        initial_activities = self.env['mail.activity'].search_count([
            ('res_model', '=', 'bp.barber.appointment'),
            ('res_id', '=', appointment.id)
        ])
        
        # Mark as no-show
        appointment.action_no_show()
        
        # Check that activity was created
        final_activities = self.env['mail.activity'].search_count([
            ('res_model', '=', 'bp.barber.appointment'),
            ('res_id', '=', appointment.id)
        ])
        
        self.assertGreater(final_activities, initial_activities, "No-show activity should be created")
        
        # Check that follow-up email was logged
        messages = appointment.message_ids.filtered(
            lambda m: 'Email sent' in (m.body or '') or 'Follow up' in (m.body or '')
        )
        self.assertTrue(len(messages) > 0, "No-show follow-up should be logged")

    def test_notification_service_settings(self):
        """Test notification service settings retrieval"""
        service = self.env['bp.barber.notification.service']
        settings = service.get_notification_settings()
        
        # Check expected keys exist
        expected_keys = [
            'notify_on_confirm', 'reminder_enabled', 'reminder_hours_primary',
            'reminder_hours_secondary', 'send_ics', 'followup_noshow'
        ]
        
        for key in expected_keys:
            self.assertIn(key, settings)
            
        # Check default values
        self.assertTrue(settings['notify_on_confirm'])
        self.assertTrue(settings['reminder_enabled'])
        self.assertEqual(settings['reminder_hours_primary'], 24)


class TestBarberNotificationPortal(HttpCase):
    """Test HTTP portal for appointment confirmation/cancellation"""

    def setUp(self):
        super().setUp()
        
        # Create test data
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@customer.com'
        })
        
        self.barber = self.env['bp.barber.barber'].create({
            'name': 'Test Barber',
            'phone': '123-456-7890'
        })
        
        self.service = self.env['bp.barber.service'].create({
            'name': 'Test Haircut',
            'list_price': 25.00,
            'duration_minutes': 30
        })

    def test_portal_test_endpoint(self):
        """Test portal test endpoint"""
        response = self.url_open('/barber/apt/test')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Notification Portal', response.content)

    def test_token_confirm_route(self):
        """Test appointment confirmation via token"""
        # Create confirmed appointment
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() + timedelta(hours=24),
            'state': 'confirmed',
        })
        
        # Test confirmation URL
        url = f'/barber/apt/{appointment.name}/{appointment.appointment_token}/confirm'
        response = self.url_open(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Appointment Confirmed', response.content)

    def test_token_cancel_route(self):
        """Test appointment cancellation via token"""
        # Create confirmed appointment
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() + timedelta(hours=24),
            'state': 'confirmed',
        })
        
        # Test cancellation URL
        url = f'/barber/apt/{appointment.name}/{appointment.appointment_token}/cancel'
        response = self.url_open(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Appointment Cancelled', response.content)
        
        # Verify appointment state changed
        appointment.refresh()
        self.assertEqual(appointment.state, 'cancelled')

    def test_invalid_token_route(self):
        """Test invalid token handling"""
        # Test with invalid token
        url = '/barber/apt/INVALID/invalid-token/confirm'
        response = self.url_open(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid Link', response.content)

    def test_appointment_state_validation(self):
        """Test that only valid states can be confirmed/cancelled"""
        # Create done appointment (cannot be cancelled)
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() - timedelta(hours=1),
            'state': 'done',
        })
        
        # Try to cancel done appointment
        url = f'/barber/apt/{appointment.name}/{appointment.appointment_token}/cancel'
        response = self.url_open(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cannot Cancel', response.content)
        
        # Verify state didn't change
        appointment.refresh()
        self.assertEqual(appointment.state, 'done')