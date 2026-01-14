# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import UserError
from datetime import datetime, timedelta


@tagged('post_install', '-at_install')
class TestAppointmentCore(TransactionCase):
    """Test appointment core functionality"""
    
    def setUp(self):
        super().setUp()
        self.env = self.env(context=dict(self.env.context, tracking_disable=True))
        
        # Create test data
        self.company = self.env.company
        
        # Create test service
        self.service = self.env['bp.barber.service'].create({
            'name': 'Test Cut',
            'code': 'TCUT',
            'duration_minutes': 45,
            'list_price': 25.00,
        })
        
        self.service2 = self.env['bp.barber.service'].create({
            'name': 'Test Shave',
            'code': 'TSHV',
            'duration_minutes': 30,
            'list_price': 15.00,
        })
        
        # Create test chair
        self.chair = self.env['bp.barber.chair'].create({
            'name': 'Test Chair',
            'code': 'TC1',
        })
        
        # Create test barber
        self.barber = self.env['bp.barber.barber'].create({
            'name': 'Test Barber',
            'barber_code': 'TB1',
            'chair_id': self.chair.id,
        })
        
        # Create test partner
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'phone': '+1-555-TEST',
            'email': 'test@customer.com',
        })
        
    def test_flow_confirm_start_finish_locks(self):
        """Test complete appointment flow and locking behavior"""
        # Create appointment
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() + timedelta(hours=1),
        })
        
        # Test flow: draft -> confirmed -> in_service -> done
        self.assertEqual(appointment.state, 'draft')
        
        # Confirm
        appointment.action_confirm()
        self.assertEqual(appointment.state, 'confirmed')
        
        # Start service
        appointment.action_start_service()
        self.assertEqual(appointment.state, 'in_service')
        
        # Finish service
        original_price_total = appointment.price_total
        appointment.action_finish_service()
        self.assertEqual(appointment.state, 'done')
        
        # Test locking - should not be able to modify done appointments
        with self.assertRaises(UserError, msg="Done appointments are locked and cannot be modified."):
            appointment.write({'discount_percent': 10.0})
        
        # Verify price didn't change
        appointment.refresh()
        self.assertEqual(appointment.price_total, original_price_total)
        
        # Test that chatter fields are still writable
        try:
            appointment.message_post(body="Test message on done appointment")
        except UserError:
            self.fail("Should be able to post messages on done appointments")
            
    def test_computes_duration_and_end(self):
        """Test duration and end time computation"""
        start_time = datetime(2025, 1, 10, 9, 0)  # 09:00
        
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id, self.service2.id])],  # 45 + 30 = 75 minutes
            'start_datetime': start_time,
        })
        
        # Check computations
        expected_duration = 45 + 30  # 75 minutes
        expected_end = start_time + timedelta(minutes=75)  # 10:15
        
        self.assertEqual(appointment.duration_minutes, expected_duration)
        self.assertEqual(appointment.end_datetime, expected_end)
        
    def test_requirements_on_confirm(self):
        """Test validation requirements for confirmation"""
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'service_ids': [(6, 0, [self.service.id])],
        })
        
        # Test missing barber_id
        with self.assertRaises(UserError, msg="Barber is required to confirm appointment."):
            appointment.action_confirm()
        
        # Add barber but no start_datetime
        appointment.barber_id = self.barber.id
        with self.assertRaises(UserError, msg="Start time is required to confirm appointment."):
            appointment.action_confirm()
        
        # Add start_datetime - should work now
        appointment.start_datetime = datetime.now() + timedelta(hours=1)
        appointment.action_confirm()  # Should not raise
        self.assertEqual(appointment.state, 'confirmed')
        
    def test_no_show_creates_activity(self):
        """Test that no-show creates follow-up activity"""
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() + timedelta(hours=1),
        })
        
        # Confirm first
        appointment.action_confirm()
        
        # Mark as no-show
        appointment.action_no_show()
        
        # Check state
        self.assertEqual(appointment.state, 'no_show')
        
        # Check activity created
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'bp.barber.appointment'),
            ('res_id', '=', appointment.id)
        ])
        self.assertTrue(activities, "No-show should create a follow-up activity")
        
        # Check activity content
        activity = activities[0]
        self.assertIn('no-show', activity.summary.lower())
        
    def test_price_computations(self):
        """Test price calculations with discount"""
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id, self.service2.id])],  # 25 + 15 = 40
            'start_datetime': datetime.now() + timedelta(hours=1),
            'discount_percent': 10.0,
        })
        
        expected_subtotal = 25.00 + 15.00  # 40.00
        expected_discount = expected_subtotal * 0.10  # 4.00
        expected_total = expected_subtotal - expected_discount  # 36.00
        
        self.assertEqual(appointment.price_subtotal, expected_subtotal)
        self.assertEqual(appointment.price_total, expected_total)
        
    def test_sequence_generation(self):
        """Test appointment number sequence generation"""
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'service_ids': [(6, 0, [self.service.id])],
        })
        
        # Should have generated a number from sequence
        self.assertNotEqual(appointment.name, 'New')
        self.assertTrue(appointment.name.startswith('APT/'))
        
    def test_chair_onchange(self):
        """Test chair auto-fill from barber"""
        appointment = self.env['bp.barber.appointment'].new({
            'partner_id': self.partner.id,
            'service_ids': [(6, 0, [self.service.id])],
        })
        
        # Simulate onchange
        appointment.barber_id = self.barber
        appointment._onchange_barber_id()
        
        self.assertEqual(appointment.chair_id, self.barber.chair_id)
        
    def test_state_transitions(self):
        """Test all state transition methods"""
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() + timedelta(hours=1),
        })
        
        # Test cancel from draft
        appointment.action_cancel()
        self.assertEqual(appointment.state, 'cancelled')
        
        # Reset to draft for other tests
        appointment.state = 'draft'
        
        # Test confirm -> cancel
        appointment.action_confirm()
        appointment.action_cancel()
        self.assertEqual(appointment.state, 'cancelled')
        
        # Reset and test full flow
        appointment.state = 'draft'
        appointment.action_confirm()
        appointment.action_start_service()
        appointment.action_cancel()
        self.assertEqual(appointment.state, 'cancelled')