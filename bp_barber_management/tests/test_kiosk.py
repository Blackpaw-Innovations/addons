# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, HttpCase
from odoo.exceptions import AccessDenied
from datetime import datetime, timedelta, date
import json
import logging

_logger = logging.getLogger(__name__)


class TestBarberKiosk(TransactionCase):
    """Test barber kiosk functionality"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test barber
        cls.barber = cls.env['bp.barber.barber'].create({
            'name': 'Test Barber',
            'phone': '123-456-7890',
            'email': 'testbarber@example.com',
            'color': 3
        })
        
        # Create test service
        cls.service = cls.env['bp.barber.service'].create({
            'name': 'Test Haircut',
            'list_price': 25.00,
            'duration_minutes': 30
        })
        
        # Create test chair
        cls.chair = cls.env['bp.barber.chair'].create({
            'name': 'Test Chair',
            'barber_id': cls.barber.id
        })

    def test_kiosk_settings_validation(self):
        """Test kiosk settings validation"""
        # Test valid refresh interval
        settings = self.env['res.config.settings'].create({
            'bp_barber_kiosk_refresh_seconds': 10
        })
        settings._check_refresh_interval()  # Should not raise
        
        # Test invalid refresh interval (too low)
        with self.assertRaises(Exception):
            settings = self.env['res.config.settings'].create({
                'bp_barber_kiosk_refresh_seconds': 3
            })
            settings._check_refresh_interval()
        
        # Test invalid refresh interval (too high)
        with self.assertRaises(Exception):
            settings = self.env['res.config.settings'].create({
                'bp_barber_kiosk_refresh_seconds': 200
            })
            settings._check_refresh_interval()

    def test_kiosk_settings_storage(self):
        """Test that kiosk settings are properly stored and retrieved"""
        # Set test values
        settings = self.env['res.config.settings'].create({
            'bp_barber_kiosk_public_enabled': True,
            'bp_barber_kiosk_token': 'test_token_123',
            'bp_barber_kiosk_refresh_seconds': 15
        })
        settings.set_values()
        
        # Retrieve and verify
        new_settings = self.env['res.config.settings'].create({})
        values = new_settings.get_values()
        
        self.assertTrue(values['bp_barber_kiosk_public_enabled'])
        self.assertEqual(values['bp_barber_kiosk_token'], 'test_token_123')
        self.assertEqual(values['bp_barber_kiosk_refresh_seconds'], 15)

    def test_kiosk_service_settings(self):
        """Test kiosk service settings retrieval"""
        # Set some test parameters
        self.env['ir.config_parameter'].sudo().set_param(
            'bp_barber_management.kiosk_public_enabled', 'True'
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'bp_barber_management.kiosk_token', 'test_token'
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'bp_barber_management.kiosk_refresh_seconds', '20'
        )
        
        kiosk_service = self.env['bp.barber.kiosk.service']
        settings = kiosk_service.get_kiosk_settings()
        
        self.assertTrue(settings['public_enabled'])
        self.assertEqual(settings['access_token'], 'test_token')
        self.assertEqual(settings['refresh_seconds'], 20)

    def test_kiosk_data_shapes_from_appointments(self):
        """Test kiosk data structure from appointments"""
        today = date.today()
        
        # Create test appointments
        current_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=10)
        
        # Create in_service appointment (current)
        current_apt = self.env['bp.barber.appointment'].create({
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': current_time - timedelta(minutes=15),
            'duration_minutes': 30,
            'state': 'in_service',
            'partner_id': self.env['res.partner'].create({'name': 'John Doe'}).id,
            'price_total': 25.00
        })
        
        # Create confirmed appointments (next)
        next_apt1 = self.env['bp.barber.appointment'].create({
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': current_time + timedelta(minutes=30),
            'duration_minutes': 30,
            'state': 'confirmed',
            'partner_id': self.env['res.partner'].create({'name': 'Jane Smith'}).id,
            'price_total': 25.00
        })
        
        next_apt2 = self.env['bp.barber.appointment'].create({
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': current_time + timedelta(hours=1),
            'duration_minutes': 30,
            'state': 'confirmed',
            'partner_id': self.env['res.partner'].create({'name': 'Bob Johnson'}).id,
            'price_total': 25.00
        })
        
        # Get kiosk data
        kiosk_service = self.env['bp.barber.kiosk.service']
        data = kiosk_service.get_kiosk_data(company_id=self.env.company.id)
        
        # Verify structure
        self.assertIn('server_time', data)
        self.assertIn('barbers', data)
        self.assertTrue(len(data['barbers']) >= 1)
        
        # Find our test barber
        test_barber_data = None
        for barber_data in data['barbers']:
            if barber_data['id'] == self.barber.id:
                test_barber_data = barber_data
                break
        
        self.assertIsNotNone(test_barber_data)
        
        # Verify barber data structure
        self.assertEqual(test_barber_data['name'], 'Test Barber')
        self.assertEqual(test_barber_data['color'], 3)
        self.assertIn('chair', test_barber_data)
        
        # Verify "now" appointment
        self.assertIsNotNone(test_barber_data['now'])
        now_data = test_barber_data['now']
        self.assertEqual(now_data['partner'], 'John Doe')
        self.assertEqual(now_data['services'], 'Test Haircut')
        self.assertIn('remaining_min', now_data)
        
        # Verify "next" appointments
        self.assertTrue(len(test_barber_data['next']) >= 2)
        next_data = test_barber_data['next']
        
        # First next appointment should be Jane Smith
        self.assertEqual(next_data[0]['partner'], 'Jane Smith')
        self.assertEqual(next_data[0]['services'], 'Test Haircut')
        self.assertIn('eta_min', next_data[0])
        
        # Second next appointment should be Bob Johnson
        self.assertEqual(next_data[1]['partner'], 'Bob Johnson')

    def test_kiosk_data_filtering(self):
        """Test kiosk data filtering by barber IDs"""
        # Create another barber
        barber2 = self.env['bp.barber.barber'].create({
            'name': 'Another Barber',
            'phone': '987-654-3210',
            'email': 'another@example.com'
        })
        
        kiosk_service = self.env['bp.barber.kiosk.service']
        
        # Test with no filter - should get both barbers
        data = kiosk_service.get_kiosk_data()
        barber_ids = [b['id'] for b in data['barbers']]
        self.assertIn(self.barber.id, barber_ids)
        self.assertIn(barber2.id, barber_ids)
        
        # Test with filter - should get only specified barber
        data = kiosk_service.get_kiosk_data(barber_ids=[self.barber.id])
        barber_ids = [b['id'] for b in data['barbers']]
        self.assertIn(self.barber.id, barber_ids)
        self.assertNotIn(barber2.id, barber_ids)


class TestBarberKioskHttp(HttpCase):
    """Test HTTP endpoints for barber kiosk"""

    def setUp(self):
        super().setUp()
        
        # Enable kiosk and clear token for basic tests
        self.env['ir.config_parameter'].sudo().set_param(
            'bp_barber_management.kiosk_public_enabled', 'True'
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'bp_barber_management.kiosk_token', ''
        )

    def test_kiosk_page_public_enabled(self):
        """Test kiosk page access when publicly enabled"""
        # Should return 200 when enabled and no token required
        response = self.url_open('/barber/kiosk')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'bp-barber-kiosk', response.content)

    def test_kiosk_page_disabled(self):
        """Test kiosk page access when disabled"""
        # Disable kiosk
        self.env['ir.config_parameter'].sudo().set_param(
            'bp_barber_management.kiosk_public_enabled', 'False'
        )
        
        # Should return 404 when disabled
        response = self.url_open('/barber/kiosk')
        self.assertEqual(response.status_code, 404)

    def test_kiosk_requires_token_when_set(self):
        """Test token requirement when token is set"""
        # Set a token
        test_token = 'secret_kiosk_token_123'
        self.env['ir.config_parameter'].sudo().set_param(
            'bp_barber_management.kiosk_token', test_token
        )
        
        # Should return 404 without token
        response = self.url_open('/barber/kiosk')
        self.assertEqual(response.status_code, 404)
        
        # Should return 404 with wrong token
        response = self.url_open('/barber/kiosk?token=wrong_token')
        self.assertEqual(response.status_code, 404)
        
        # Should return 200 with correct token
        response = self.url_open(f'/barber/kiosk?token={test_token}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'bp-barber-kiosk', response.content)

    def test_kiosk_data_endpoint_structure(self):
        """Test kiosk data endpoint returns proper structure"""
        # Test HTTP GET endpoint
        response = self.url_open('/barber/kiosk/data')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('server_time', data)
        self.assertIn('barbers', data)
        self.assertIsInstance(data['barbers'], list)

    def test_kiosk_data_with_token(self):
        """Test kiosk data endpoint with token authentication"""
        test_token = 'data_test_token_456'
        self.env['ir.config_parameter'].sudo().set_param(
            'bp_barber_management.kiosk_token', test_token
        )
        
        # Should fail without token
        response = self.url_open('/barber/kiosk/data')
        self.assertEqual(response.status_code, 404)
        
        # Should succeed with token
        response = self.url_open(f'/barber/kiosk/data?token={test_token}')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('barbers', data)

    def test_kiosk_test_endpoint(self):
        """Test kiosk test endpoint functionality"""
        response = self.url_open('/barber/kiosk/test')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Barber Kiosk Controller Test', response.content)
        self.assertIn(b'Controller is working', response.content)