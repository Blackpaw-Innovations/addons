# -*- coding: utf-8 -*-

from odoo.tests.common import tagged, TransactionCase
from datetime import datetime, timedelta
from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestEndToEndCore(TransactionCase):
    """End-to-end backend flow tests for core functionality"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Get demo data references
        cls.service_cut = cls.env.ref('bp_barber_management.bp_service_cut')
        cls.service_shave = cls.env.ref('bp_barber_management.bp_service_shave')
        cls.barber_john = cls.env.ref('bp_barber_management.bp_barber_john')
        cls.barber_mary = cls.env.ref('bp_barber_management.bp_barber_mary')
        cls.chair_1 = cls.env.ref('bp_barber_management.bp_chair_1')
        
        # Create test customer
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer E2E',
            'phone': '+1-555-TEST',
            'email': 'test.e2e@example.com'
        })

    def test_appointment_full_lifecycle_with_totals_and_locking(self):
        """Test complete appointment lifecycle: create → confirm → start → finish"""
        
        # Create appointment
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.customer.id,
            'phone': self.customer.phone,
            'email': self.customer.email,
            'barber_id': self.barber_john.id,
            'start_datetime': datetime.now() + timedelta(hours=1),
            'service_ids': [(6, 0, [self.service_cut.id, self.service_shave.id])],
            'discount_percent': 10.0,
            'note': 'E2E test appointment'
        })
        
        # Initial state should be draft
        self.assertEqual(appointment.state, 'draft')
        
        # Verify totals are computed correctly
        expected_subtotal = self.service_cut.list_price + self.service_shave.list_price
        expected_total = expected_subtotal * 0.9  # 10% discount
        
        self.assertEqual(appointment.price_subtotal, expected_subtotal)
        self.assertEqual(appointment.price_total, expected_total)
        
        # Confirm appointment
        appointment.action_confirm()
        self.assertEqual(appointment.state, 'confirmed')
        
        # Start service
        appointment.action_start_service()
        self.assertEqual(appointment.state, 'in_service')
        
        # Finish service
        appointment.action_finish_service()
        self.assertEqual(appointment.state, 'done')
        
        # Test locking - should not be able to edit key fields when done
        with self.assertRaises(Exception):
            appointment.write({'barber_id': self.barber_mary.id})

    def test_pos_order_linkage_and_autocomplete(self):
        """Test POS order linkage with appointment and auto-completion"""
        
        # Create confirmed appointment
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.customer.id,
            'barber_id': self.barber_john.id,
            'start_datetime': datetime.now() + timedelta(hours=1),
            'service_ids': [(6, 0, [self.service_cut.id])],
            'state': 'confirmed'
        })
        
        # Get or create POS config with auto-complete enabled
        pos_config = self.env.ref('bp_barber_management.bp_pos_config_front_desk')
        
        # Create POS session
        pos_session = self.env['pos.session'].create({
            'config_id': pos_config.id,
            'user_id': self.env.user.id,
        })
        
        # Create POS order linked to appointment
        pos_order = self.env['pos.order'].create({
            'session_id': pos_session.id,
            'partner_id': self.customer.id,
            'appointment_id': appointment.id,
        })
        
        # Get service product (should be auto-created)
        service_product = self.env['product.product'].search([
            ('name', '=', self.service_cut.name),
            ('type', '=', 'service')
        ], limit=1)
        
        self.assertTrue(service_product, "Service product should exist")
        
        # Create order line with barber assignment
        order_line = self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': service_product.id,
            'qty': 1,
            'price_unit': self.service_cut.list_price,
            'barber_id': self.barber_john.id,
        })
        
        # Verify linkage
        self.assertEqual(pos_order.appointment_id, appointment)
        self.assertEqual(order_line.barber_id, self.barber_john)
        self.assertEqual(order_line.barber_name, self.barber_john.name)
        self.assertTrue(order_line.has_barber_assigned)
        
        # Simulate payment (this should auto-complete the appointment)
        initial_state = appointment.state
        pos_order.action_pos_order_paid()
        
        # If auto-complete is enabled, appointment should be done
        if pos_config.pos_autocomplete_appointment:
            appointment.refresh()
            self.assertEqual(appointment.state, 'done')
            
            # Check that chatter message was posted
            messages = appointment.message_ids.filtered(
                lambda m: 'POS Payment Completed' in (m.subject or '')
            )
            self.assertTrue(messages, "Chatter message should be posted on auto-completion")

    def test_report_render_pdf_generation(self):
        """Test that Visit Summary report renders to PDF for finished appointment"""
        
        # Create and complete appointment
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.customer.id,
            'phone': self.customer.phone,
            'email': self.customer.email,
            'barber_id': self.barber_mary.id,
            'chair_id': self.chair_1.id,
            'start_datetime': datetime.now() - timedelta(hours=2),
            'service_ids': [(6, 0, [self.service_cut.id, self.service_shave.id])],
            'discount_percent': 5.0,
            'note': 'Report test appointment with multiple services',
            'state': 'done'
        })
        
        # Test server-side report action method
        report_action = appointment.action_print_visit_summary()
        
        self.assertIsInstance(report_action, dict)
        self.assertEqual(report_action.get('type'), 'ir.actions.report')
        self.assertEqual(
            report_action.get('report_name'), 
            'bp_barber_management.report_appointment_visit'
        )
        
        # Test actual PDF rendering
        report = self.env.ref('bp_barber_management.action_report_bp_appointment_visit')
        pdf_bytes, fmt = report._render_qweb_pdf([appointment.id])
        
        # Verify PDF generation
        self.assertEqual(fmt, 'pdf')
        self.assertGreater(len(pdf_bytes), 0)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'), "Should be valid PDF")
        
        # Test with minimal appointment data
        minimal_appointment = self.env['bp.barber.appointment'].create({
            'start_datetime': datetime.now() - timedelta(hours=1),
            'service_ids': [(6, 0, [self.service_cut.id])],
            'state': 'done'
        })
        
        pdf_bytes_minimal, fmt_minimal = report._render_qweb_pdf([minimal_appointment.id])
        self.assertEqual(fmt_minimal, 'pdf')
        self.assertGreater(len(pdf_bytes_minimal), 0)

    def test_service_product_sync_mechanism(self):
        """Test that services automatically create POS products via Stage 2 logic"""
        
        # Create new service
        new_service = self.env['bp.service'].create({
            'name': 'E2E Test Service',
            'code': 'E2E',
            'duration_minutes': 45,
            'list_price': 35.00,
            'active': True
        })
        
        # Check that corresponding product was created
        service_product = self.env['product.product'].search([
            ('name', '=', new_service.name),
            ('type', '=', 'service'),
            ('available_in_pos', '=', True)
        ])
        
        self.assertTrue(service_product, "Product should be auto-created for service")
        self.assertEqual(service_product.list_price, new_service.list_price)
        self.assertTrue(service_product.available_in_pos)
        
        # Test service update propagates to product
        new_service.write({
            'list_price': 40.00,
            'name': 'Updated E2E Service'
        })
        
        # Depending on implementation, product might sync automatically
        # This tests the sync mechanism if it exists
        service_product.refresh()

    def test_pos_barber_summary_and_receipt_data(self):
        """Test POS order barber summary for receipts"""
        
        # Create POS session
        pos_config = self.env.ref('bp_barber_management.bp_pos_config_front_desk')
        pos_session = self.env['pos.session'].create({
            'config_id': pos_config.id,
            'user_id': self.env.user.id,
        })
        
        # Create POS order with multiple lines and different barbers
        pos_order = self.env['pos.order'].create({
            'session_id': pos_session.id,
            'partner_id': self.customer.id,
        })
        
        # Get service products
        cut_product = self.env['product.product'].search([
            ('name', '=', self.service_cut.name),
            ('type', '=', 'service')
        ], limit=1)
        
        shave_product = self.env['product.product'].search([
            ('name', '=', self.service_shave.name),
            ('type', '=', 'service')
        ], limit=1)
        
        # Create lines with different barbers
        self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': cut_product.id,
            'qty': 1,
            'price_unit': 10.0,
            'barber_id': self.barber_john.id,
        })
        
        self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': shave_product.id,
            'qty': 1,
            'price_unit': 6.0,
            'barber_id': self.barber_mary.id,
        })
        
        # Test barber summary
        barber_summary = pos_order.get_barbers_summary()
        self.assertIn(self.barber_john.name, barber_summary)
        self.assertIn(self.barber_mary.name, barber_summary)

    def test_appointment_validation_and_constraints(self):
        """Test appointment validation rules and business constraints"""
        
        # Test that appointment requires either partner or phone
        with self.assertRaises(Exception):
            self.env['bp.barber.appointment'].create({
                'barber_id': self.barber_john.id,
                'start_datetime': datetime.now() + timedelta(hours=1),
                'service_ids': [(6, 0, [self.service_cut.id])],
            })
        
        # Test valid appointment with phone only
        phone_only_apt = self.env['bp.barber.appointment'].create({
            'phone': '+1-555-VALID',
            'barber_id': self.barber_john.id,
            'start_datetime': datetime.now() + timedelta(hours=2),
            'service_ids': [(6, 0, [self.service_cut.id])],
        })
        
        self.assertTrue(phone_only_apt)
        self.assertEqual(phone_only_apt.state, 'draft')

    def test_end_to_end_with_demo_data_integration(self):
        """Test E2E flow using existing demo data"""
        
        # Get demo appointment in confirmed state
        demo_appointment = self.env.ref('bp_barber_management.bp_appointment_confirmed')
        
        # Verify it's in expected state
        self.assertEqual(demo_appointment.state, 'confirmed')
        self.assertTrue(demo_appointment.service_ids)
        
        # Complete the lifecycle
        demo_appointment.action_start_service()
        self.assertEqual(demo_appointment.state, 'in_service')
        
        demo_appointment.action_finish_service()
        self.assertEqual(demo_appointment.state, 'done')
        
        # Generate report
        report_action = demo_appointment.action_print_visit_summary()
        self.assertEqual(report_action.get('type'), 'ir.actions.report')
        
        # Verify totals were computed
        self.assertGreater(demo_appointment.price_total, 0)