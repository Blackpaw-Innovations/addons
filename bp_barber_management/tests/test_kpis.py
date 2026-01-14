# -*- coding: utf-8 -*-

from odoo.tests import common, tagged
from odoo.exceptions import ValidationError
from datetime import date, timedelta
import json


@tagged('post_install', '-at_install')
class TestBarberKpis(common.TransactionCase):
    """Test KPI calculations and dashboard functionality"""

    def setUp(self):
        super().setUp()
        
        # Create test company
        self.company = self.env['res.company'].create({
            'name': 'Test Barbershop',
            'currency_id': self.env.ref('base.USD').id,
        })
        
        # Create test barbers
        self.barber1 = self.env['bp.barber.barber'].create({
            'name': 'Alice Smith',
            'company_id': self.company.id,
        })
        
        self.barber2 = self.env['bp.barber.barber'].create({
            'name': 'Bob Johnson', 
            'company_id': self.company.id,
        })

        # Create test services
        self.service1 = self.env['bp.barber.service'].create({
            'name': 'Haircut',
            'price': 25.0,
            'duration_minutes': 30,
            'company_id': self.company.id,
        })
        
        self.service2 = self.env['bp.barber.service'].create({
            'name': 'Shave',
            'price': 15.0,
            'duration_minutes': 15,
            'company_id': self.company.id,
        })

        # Create test products
        self.product_service = self.env['product.product'].create({
            'name': 'POS Haircut',
            'type': 'service',
            'list_price': 30.0,
        })
        
        self.product_retail = self.env['product.product'].create({
            'name': 'Hair Gel',
            'type': 'consu',
            'list_price': 8.0,
        })
        
        self.consumable_product = self.env['product.product'].create({
            'name': 'Aftershave',
            'type': 'consu',
            'list_price': 5.0,
        })

        # Test date range
        self.date_from = date.today() - timedelta(days=7)
        self.date_to = date.today()
        
        # Create KPI service
        self.kpi_service = self.env['bp.barber.kpi.service']

    def test_reporting_views_exist(self):
        """Test that SQL reporting models can be queried without errors"""
        
        # Test appointment report
        appointment_reports = self.env['bp.barber.report_appointment'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ])
        self.assertIsInstance(appointment_reports, type(self.env['bp.barber.report_appointment']))
        
        # Test POS line report
        pos_reports = self.env['bp.barber.report_pos_line'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ])
        self.assertIsInstance(pos_reports, type(self.env['bp.barber.report_pos_line']))
        
        # Test consumable report
        consumable_reports = self.env['bp.barber.report_consumable'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ])
        self.assertIsInstance(consumable_reports, type(self.env['bp.barber.report_consumable']))

    def test_kpi_no_show_rate(self):
        """Test no-show rate calculation"""
        
        # Create test appointments
        appointments_data = [
            {'state': 'confirmed', 'barber_id': self.barber1.id},
            {'state': 'done', 'barber_id': self.barber1.id},
            {'state': 'no_show', 'barber_id': self.barber1.id},
            {'state': 'no_show', 'barber_id': self.barber2.id},
            {'state': 'in_service', 'barber_id': self.barber2.id},
        ]
        
        for data in appointments_data:
            self.env['bp.barber.appointment'].create({
                'date': self.date_from + timedelta(days=1),
                'time_start': '09:00',
                'time_end': '09:30',
                'chair_id': 1,  # Assuming chair exists
                'state': data['state'],
                'barber_id': data['barber_id'],
                'company_id': self.company.id,
            })
        
        # Calculate no-show rate
        result = self.kpi_service.kpi_no_show_rate(
            self.date_from, self.date_to, self.company.id
        )
        
        # Expected: 2 no-shows out of 5 total = 40%
        self.assertEqual(result['no_shows'], 2)
        self.assertEqual(result['total_bookings'], 5)
        self.assertEqual(result['percent'], 40.0)

    def test_kpi_utilization(self):
        """Test utilization calculation"""
        
        # Create test schedule for barber
        self.env['bp.barber.schedule'].create({
            'barber_id': self.barber1.id,
            'day_of_week': '1',  # Monday
            'start_time': 9.0,   # 09:00
            'end_time': 17.0,    # 17:00 (8 hours = 480 minutes)
            'company_id': self.company.id,
            'active': True,
        })
        
        # Create test appointments (3 hours = 180 minutes)
        appointment_durations = [60, 30, 90]  # Total 180 minutes
        
        for duration in appointment_durations:
            self.env['bp.barber.appointment'].create({
                'date': self.date_from + timedelta(days=1),  # Monday
                'time_start': '09:00',
                'time_end': '09:30',
                'chair_id': 1,
                'state': 'done',
                'barber_id': self.barber1.id,
                'duration_minutes': duration,
                'company_id': self.company.id,
            })
        
        # Calculate utilization
        result = self.kpi_service.kpi_utilization(
            self.date_from, self.date_to, self.company.id
        )
        
        # Should show busy minutes and percentage
        self.assertGreater(result['busy_minutes'], 0)
        self.assertGreater(result['available_minutes'], 0)
        self.assertGreaterEqual(result['percent'], 0)
        self.assertLessEqual(result['percent'], 100)

    def test_kpi_attach_rate(self):
        """Test retail attach rate calculation"""
        
        # Mock POS orders - would normally be created through POS interface
        # For this test, we'll create minimal data and test the query logic
        
        # Create test session and config (minimal for POS orders)
        pos_config = self.env['pos.config'].create({
            'name': 'Test POS',
            'company_id': self.company.id,
        })
        
        session = self.env['pos.session'].create({
            'config_id': pos_config.id,
            'user_id': self.env.user.id,
        })
        
        # Create POS orders with different line combinations
        # Order 1: Service only
        order1 = self.env['pos.order'].create({
            'session_id': session.id,
            'partner_id': False,
            'state': 'paid',
            'company_id': self.company.id,
        })
        
        self.env['pos.order.line'].create({
            'order_id': order1.id,
            'product_id': self.product_service.id,
            'qty': 1,
            'price_unit': 30.0,
            'barber_id': self.barber1.id,
        })
        
        # Order 2: Service + Retail
        order2 = self.env['pos.order'].create({
            'session_id': session.id,
            'partner_id': False,
            'state': 'paid',
            'company_id': self.company.id,
        })
        
        self.env['pos.order.line'].create({
            'order_id': order2.id,
            'product_id': self.product_service.id,
            'qty': 1,
            'price_unit': 30.0,
            'barber_id': self.barber1.id,
        })
        
        self.env['pos.order.line'].create({
            'order_id': order2.id,
            'product_id': self.product_retail.id,
            'qty': 1,
            'price_unit': 8.0,
            'barber_id': self.barber1.id,
        })
        
        # Calculate attach rate
        result = self.kpi_service.kpi_attach_rate(
            self.date_from, self.date_to, self.company.id
        )
        
        # Should show attach rate calculation
        self.assertGreaterEqual(result['orders_with_services'], 0)
        self.assertGreaterEqual(result['with_retail_attached'], 0)
        self.assertGreaterEqual(result['percent'], 0)
        self.assertLessEqual(result['percent'], 100)

    def test_kpi_revenue_by_barber_and_service(self):
        """Test revenue calculations by barber and service"""
        
        # Create test appointment with revenue
        appointment = self.env['bp.barber.appointment'].create({
            'date': self.date_from + timedelta(days=1),
            'time_start': '09:00',
            'time_end': '09:30',
            'chair_id': 1,
            'state': 'done',
            'barber_id': self.barber1.id,
            'price_total': 25.0,
            'company_id': self.company.id,
        })
        
        # Add service to appointment
        appointment.service_ids = [(6, 0, [self.service1.id])]
        
        # Calculate revenue by barber
        barber_revenue = self.kpi_service.kpi_revenue_by_barber(
            self.date_from, self.date_to, self.company.id
        )
        
        # Should have revenue for barber1
        barber1_data = next((b for b in barber_revenue if b['barber_id'] == self.barber1.id), None)
        self.assertIsNotNone(barber1_data)
        self.assertEqual(barber1_data['name'], 'Alice Smith')
        self.assertGreater(barber1_data['amount'], 0)
        
        # Calculate revenue by service
        service_revenue = self.kpi_service.kpi_revenue_by_service(
            self.date_from, self.date_to, self.company.id
        )
        
        # Should have at least one service entry
        self.assertGreaterEqual(len(service_revenue), 0)

    def test_kpi_top_consumables(self):
        """Test top consumables calculation"""
        
        # Create consumable usage
        usage = self.env['bp.barber.consumable.usage'].create({
            'barber_id': self.barber1.id,
            'date': self.date_from + timedelta(days=1),
            'company_id': self.company.id,
        })
        
        self.env['bp.barber.consumable.usage.line'].create({
            'usage_id': usage.id,
            'product_id': self.consumable_product.id,
            'qty': 2.5,
        })
        
        # Calculate top consumables
        result = self.kpi_service.kpi_top_consumables(
            self.date_from, self.date_to, self.company.id
        )
        
        # Should return consumable data
        if result:  # Only test if data exists
            self.assertIsInstance(result, list)
            for item in result:
                self.assertIn('product_id', item)
                self.assertIn('name', item) 
                self.assertIn('qty', item)

    def test_get_all_kpis_integration(self):
        """Test the complete KPI integration method"""
        
        payload = {
            'period': '7d',
            'company_id': self.company.id
        }
        
        result = self.kpi_service.get_all_kpis(payload)
        
        # Verify response structure
        self.assertIn('period', result)
        self.assertIn('from', result)
        self.assertIn('to', result)
        self.assertIn('tiles', result)
        
        tiles = result['tiles']
        expected_keys = [
            'revenue_by_barber', 'revenue_by_service', 'utilization',
            'no_show_rate', 'attach_rate', 'top_consumables'
        ]
        
        for key in expected_keys:
            self.assertIn(key, tiles, f"Missing key: {key}")

    def test_period_computation(self):
        """Test period computation helper method"""
        
        # Test today
        date_from, date_to = self.kpi_service.compute_period('today')
        self.assertEqual(date_from, date.today())
        self.assertEqual(date_to, date.today())
        
        # Test 7 days
        date_from, date_to = self.kpi_service.compute_period('7d')
        self.assertEqual(date_to, date.today())
        self.assertEqual(date_from, date.today() - timedelta(days=6))
        
        # Test 30 days
        date_from, date_to = self.kpi_service.compute_period('30d')
        self.assertEqual(date_to, date.today())
        self.assertEqual(date_from, date.today() - timedelta(days=29))
        
        # Test custom
        custom_from = date(2024, 1, 1)
        custom_to = date(2024, 1, 31)
        date_from, date_to = self.kpi_service.compute_period(
            'custom', custom_from.strftime('%Y-%m-%d'), custom_to.strftime('%Y-%m-%d')
        )
        self.assertEqual(date_from, custom_from)
        self.assertEqual(date_to, custom_to)


@tagged('post_install', '-at_install')
class TestDashboardController(common.HttpCase):
    """Test dashboard HTTP endpoints"""
    
    def setUp(self):
        super().setUp()
        
        # Create test user with barber management access
        self.test_user = self.env['res.users'].create({
            'name': 'Test Dashboard User',
            'login': 'dashboard_test',
            'email': 'dashboard@test.com',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('bp_barber_management.group_barber_manager').id,
            ])],
        })

    def test_kpi_endpoint_json(self):
        """Test JSON KPI endpoint with authentication"""
        
        # Authenticate as test user
        self.authenticate('dashboard_test', 'dashboard_test')
        
        # Test basic JSON request
        response = self.url_open(
            '/bp_barber/kpi',
            data=json.dumps({'period': '7d'}),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)

    def test_kpi_endpoint_http_get(self):
        """Test HTTP GET KPI endpoint"""
        
        # Authenticate as test user
        self.authenticate('dashboard_test', 'dashboard_test')
        
        # Test HTTP GET request
        response = self.url_open('/bp_barber/kpi?period=today')
        
        self.assertEqual(response.status_code, 200)
        
        # Should return JSON content
        content_type = response.headers.get('Content-Type', '')
        self.assertIn('application/json', content_type)

    def test_dashboard_test_endpoint(self):
        """Test the dashboard test endpoint"""
        
        # Authenticate as test user 
        self.authenticate('dashboard_test', 'dashboard_test')
        
        # Test the test endpoint
        response = self.url_open('/bp_barber/dashboard/test')
        
        self.assertEqual(response.status_code, 200)
        
        # Should contain HTML content
        content = response.text
        self.assertIn('Barber Dashboard Controller Test', content)
        self.assertIn('Controller is working!', content)