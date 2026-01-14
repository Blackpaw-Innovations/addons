# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from unittest.mock import patch


class TestPOSBarberIntegration(TransactionCase):
    """Test suite for POS-Barber Management integration"""

    def setUp(self):
        super().setUp()
        
        # Create test data
        self.company = self.env.company
        
        # Create test barbers
        self.barber1 = self.env['bp.barber'].create({
            'name': 'John Stylist',
            'phone': '+1234567890',
            'color_index': 1,
        })
        
        self.barber2 = self.env['bp.barber'].create({
            'name': 'Jane Cutter',
            'phone': '+1234567891',
            'color_index': 2,
        })
        
        # Create test service
        self.service = self.env['bp.service'].create({
            'name': 'Premium Haircut',
            'duration': 45,
            'price': 50.0,
        })
        
        # Create test product
        self.product = self.env['product.product'].create({
            'name': 'Premium Haircut',
            'type': 'service',
            'list_price': 50.0,
            'available_in_pos': True,
        })
        
        # Create POS configuration
        self.pos_config = self.env['pos.config'].create({
            'name': 'Test Barber POS',
            'enable_barber_mode': True,
            'barber_scope': 'all',
            'auto_complete_appointments': True,
        })
        
        # Create test appointment
        appointment_time = datetime.now() + timedelta(hours=1)
        self.appointment = self.env['bp.appointment'].create({
            'partner_id': self.env['res.partner'].create({
                'name': 'Test Customer',
                'phone': '+1987654321'
            }).id,
            'barber_id': self.barber1.id,
            'service_id': self.service.id,
            'appointment_time': appointment_time,
            'state': 'confirmed',
            'total_price': 50.0,
        })

    def test_pos_order_appointment_linking(self):
        """Test linking appointments to POS orders"""
        
        # Create POS order
        pos_order = self.env['pos.order'].create({
            'session_id': self._create_pos_session().id,
            'partner_id': self.appointment.partner_id.id,
            'appointment_id': self.appointment.id,
        })
        
        # Verify appointment is linked
        self.assertEqual(pos_order.appointment_id, self.appointment)
        self.assertEqual(pos_order.partner_id, self.appointment.partner_id)

    def test_pos_order_line_barber_assignment(self):
        """Test barber assignment on order lines"""
        
        # Create POS session and order
        session = self._create_pos_session()
        pos_order = self.env['pos.order'].create({
            'session_id': session.id,
            'partner_id': self.appointment.partner_id.id,
        })
        
        # Create order line with barber
        order_line = self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': self.product.id,
            'qty': 1,
            'price_unit': 50.0,
            'barber_id': self.barber1.id,
        })
        
        # Verify barber assignment
        self.assertEqual(order_line.barber_id, self.barber1)
        self.assertEqual(order_line.barber_name, 'John Stylist')

    def test_appointment_auto_completion(self):
        """Test automatic appointment completion on payment"""
        
        # Create POS session and order
        session = self._create_pos_session()
        pos_order = self.env['pos.order'].create({
            'session_id': session.id,
            'partner_id': self.appointment.partner_id.id,
            'appointment_id': self.appointment.id,
            'amount_total': 50.0,
        })
        
        # Create order line
        self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': self.product.id,
            'qty': 1,
            'price_unit': 50.0,
            'barber_id': self.barber1.id,
        })
        
        # Verify initial appointment state
        self.assertEqual(self.appointment.state, 'confirmed')
        
        # Simulate payment completion
        pos_order.action_pos_order_paid()
        
        # Verify appointment is auto-completed
        self.assertEqual(self.appointment.state, 'done')
        self.assertEqual(self.appointment.pos_order_id, pos_order)

    def test_appointment_loading_to_order(self):
        """Test loading appointment data into POS order"""
        
        # Create POS session and order
        session = self._create_pos_session()
        order = self.env['pos.order'].create({
            'session_id': session.id,
        })
        
        # Mock the load appointment functionality
        # This would typically be called from JavaScript
        lines_data = [{
            'product_id': self.product.id,
            'qty': 1,
            'price_unit': self.service.price,
            'barber_id': self.appointment.barber_id.id,
        }]
        
        # Create lines from appointment data
        for line_data in lines_data:
            self.env['pos.order.line'].create({
                'order_id': order.id,
                **line_data
            })
        
        # Link appointment
        order.appointment_id = self.appointment.id
        order.partner_id = self.appointment.partner_id.id
        
        # Verify order structure
        self.assertEqual(len(order.lines), 1)
        self.assertEqual(order.lines[0].product_id, self.product)
        self.assertEqual(order.lines[0].barber_id, self.barber1)

    def test_pos_config_barber_scope(self):
        """Test POS configuration barber scope functionality"""
        
        # Test 'all' scope
        self.pos_config.barber_scope = 'all'
        available_barbers = self.pos_config._get_available_barbers()
        self.assertIn(self.barber1, available_barbers)
        self.assertIn(self.barber2, available_barbers)
        
        # Test 'specific' scope
        self.pos_config.barber_scope = 'specific'
        self.pos_config.barber_ids = [(6, 0, [self.barber1.id])]
        available_barbers = self.pos_config._get_available_barbers()
        self.assertIn(self.barber1, available_barbers)
        self.assertNotIn(self.barber2, available_barbers)

    def test_pos_order_barber_validation(self):
        """Test validation of barber assignments in orders"""
        
        # Create order with restricted barber scope
        self.pos_config.barber_scope = 'specific'
        self.pos_config.barber_ids = [(6, 0, [self.barber1.id])]
        
        session = self._create_pos_session()
        pos_order = self.env['pos.order'].create({
            'session_id': session.id,
        })
        
        # Try to assign unauthorized barber - should not raise error in POS
        # (validation is typically handled in the UI)
        order_line = self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': self.product.id,
            'qty': 1,
            'price_unit': 50.0,
            'barber_id': self.barber2.id,  # Not in authorized list
        })
        
        # Line should still be created (business logic allows flexibility)
        self.assertEqual(order_line.barber_id, self.barber2)

    def test_appointment_state_transitions(self):
        """Test appointment state changes through POS workflow"""
        
        session = self._create_pos_session()
        
        # Create order linked to appointment
        pos_order = self.env['pos.order'].create({
            'session_id': session.id,
            'partner_id': self.appointment.partner_id.id,
            'appointment_id': self.appointment.id,
        })
        
        # Create matching order line
        self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': self.product.id,
            'qty': 1,
            'price_unit': 50.0,
            'barber_id': self.appointment.barber_id.id,
        })
        
        # Appointment should start as confirmed
        self.assertEqual(self.appointment.state, 'confirmed')
        
        # Simulate service start (would be manual button click)
        self.appointment.action_start_service()
        self.assertEqual(self.appointment.state, 'in_service')
        
        # Complete order - should complete appointment
        pos_order.action_pos_order_paid()
        self.assertEqual(self.appointment.state, 'done')

    def test_multiple_services_appointment(self):
        """Test handling appointments with multiple services"""
        
        # Create additional service and product
        service2 = self.env['bp.service'].create({
            'name': 'Beard Trim',
            'duration': 15,
            'price': 20.0,
        })
        
        product2 = self.env['product.product'].create({
            'name': 'Beard Trim',
            'type': 'service',
            'list_price': 20.0,
            'available_in_pos': True,
        })
        
        # Create appointment with multiple services
        appointment = self.env['bp.appointment'].create({
            'partner_id': self.appointment.partner_id.id,
            'barber_id': self.barber1.id,
            'service_id': self.service.id,  # Primary service
            'appointment_time': datetime.now() + timedelta(hours=2),
            'state': 'confirmed',
            'total_price': 70.0,  # 50 + 20
        })
        
        session = self._create_pos_session()
        pos_order = self.env['pos.order'].create({
            'session_id': session.id,
            'partner_id': appointment.partner_id.id,
            'appointment_id': appointment.id,
        })
        
        # Create lines for both services
        self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': self.product.id,
            'qty': 1,
            'price_unit': 50.0,
            'barber_id': self.barber1.id,
        })
        
        self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': product2.id,
            'qty': 1,
            'price_unit': 20.0,
            'barber_id': self.barber1.id,
        })
        
        # Verify total and completion
        self.assertEqual(len(pos_order.lines), 2)
        pos_order.action_pos_order_paid()
        self.assertEqual(appointment.state, 'done')

    def _create_pos_session(self):
        """Helper to create a POS session for testing"""
        return self.env['pos.session'].create({
            'config_id': self.pos_config.id,
            'user_id': self.env.user.id,
        })

    def test_pos_receipt_barber_info(self):
        """Test that barber info appears on POS receipts"""
        
        session = self._create_pos_session()
        pos_order = self.env['pos.order'].create({
            'session_id': session.id,
            'partner_id': self.appointment.partner_id.id,
            'appointment_id': self.appointment.id,
        })
        
        order_line = self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': self.product.id,
            'qty': 1,
            'price_unit': 50.0,
            'barber_id': self.barber1.id,
        })
        
        # Test that barber info is accessible for receipt
        self.assertEqual(order_line.barber_name, 'John Stylist')
        self.assertTrue(order_line.has_barber_assigned)
        
        # Test order-level barber summary
        barbers_summary = pos_order.get_barbers_summary()
        self.assertIn('John Stylist', barbers_summary)