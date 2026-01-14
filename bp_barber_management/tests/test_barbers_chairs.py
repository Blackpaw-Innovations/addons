# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import ValidationError
from psycopg2 import IntegrityError


@tagged('post_install', '-at_install')
class TestBarbersChairs(TransactionCase):
    """Test barbers and chairs functionality"""
    
    def setUp(self):
        super().setUp()
        self.env = self.env(context=dict(self.env.context, tracking_disable=True))
        
        # Create test company if needed
        self.company = self.env.company
        
    def test_create_chair_and_barber(self):
        """Test creating a chair and a barber linked to it"""
        # Create chair
        chair = self.env['bp.barber.chair'].create({
            'name': 'Test Chair',
            'code': 'TC1',
            'is_available': True,
        })
        
        self.assertTrue(chair.active, "Chair should be active by default")
        self.assertEqual(chair.code, 'TC1', "Chair code should be set correctly")
        
        # Create barber
        barber = self.env['bp.barber.barber'].create({
            'name': 'Test Barber',
            'barber_code': 'TB1',
            'skill_level': 'mid',
            'chair_id': chair.id,
        })
        
        self.assertTrue(barber.active, "Barber should be active by default")
        self.assertEqual(barber.chair_id, chair, "Barber should be linked to the chair")
        self.assertEqual(barber.skill_level, 'mid', "Skill level should be set correctly")
        
    def test_unique_codes(self):
        """Test that duplicate codes raise integrity errors"""
        company = self.company
        
        # Create first chair
        chair1 = self.env['bp.barber.chair'].create({
            'name': 'Chair 1',
            'code': 'DUP1',
            'company_id': company.id,
        })
        
        # Try to create duplicate chair code in same company
        with self.assertRaises((ValidationError, IntegrityError)):
            self.env['bp.barber.chair'].create({
                'name': 'Chair 2',
                'code': 'DUP1',
                'company_id': company.id,
            })
        
        # Create first barber
        barber1 = self.env['bp.barber.barber'].create({
            'name': 'Barber 1',
            'barber_code': 'DUP1',
            'company_id': company.id,
        })
        
        # Try to create duplicate barber code in same company
        with self.assertRaises((ValidationError, IntegrityError)):
            self.env['bp.barber.barber'].create({
                'name': 'Barber 2',
                'barber_code': 'DUP1',
                'company_id': company.id,
            })
            
    def test_barber_chatter_available(self):
        """Test that chatter is available on barber records"""
        barber = self.env['bp.barber.barber'].create({
            'name': 'Chatter Test Barber',
            'barber_code': 'CTB1',
        })
        
        # Post a message
        message_body = "Test message for chatter functionality"
        barber.message_post(body=message_body, subject="Test Message")
        
        # Check that message exists
        messages = barber.message_ids
        self.assertTrue(messages, "Barber should have messages (chatter enabled)")
        
        # Find our test message
        test_message = messages.filtered(lambda m: message_body in (m.body or ''))
        self.assertTrue(test_message, "Test message should be found in barber messages")
        
    def test_archive_chair_does_not_block_barber(self):
        """Test that archiving a chair doesn't block the linked barber"""
        # Create chair and barber
        chair = self.env['bp.barber.chair'].create({
            'name': 'Archive Test Chair',
            'code': 'ATC1',
            'is_available': True,
        })
        
        barber = self.env['bp.barber.barber'].create({
            'name': 'Archive Test Barber',
            'barber_code': 'ATB1',
            'chair_id': chair.id,
        })
        
        # Archive the chair
        chair.active = False
        
        # Check that barber is still valid and editable
        self.assertTrue(barber.exists(), "Barber should still exist after chair archival")
        self.assertEqual(barber.chair_id, chair, "Barber should still be linked to archived chair")
        
        # Test that barber can be updated
        barber.write({'name': 'Updated Barber Name'})
        self.assertEqual(barber.name, 'Updated Barber Name', "Barber should be editable after chair archival")
        
        # Test that archived chair is not available for new barbers
        new_barber = self.env['bp.barber.barber'].create({
            'name': 'New Barber',
            'barber_code': 'NB1',
        })
        
        # The domain in chair_id field should exclude archived chairs
        available_chairs = self.env['bp.barber.chair'].search([
            ('active', '=', True), 
            ('company_id', '=', new_barber.company_id.id)
        ])
        self.assertNotIn(chair, available_chairs, "Archived chair should not be in available chairs")
        
    def test_barber_name_onchange(self):
        """Test that barber name is prefilled from partner"""
        partner = self.env['res.partner'].create({
            'name': 'Partner Test Name',
            'phone': '+1-555-TEST',
            'email': 'test@example.com',
        })
        
        barber = self.env['bp.barber.barber'].new({
            'barber_code': 'PTN1',
        })
        
        # Simulate onchange
        barber.partner_id = partner
        barber._onchange_partner_id()
        
        self.assertEqual(barber.name, partner.name, "Barber name should be prefilled from partner")
        
    def test_chair_name_get(self):
        """Test chair name_get method"""
        chair = self.env['bp.barber.chair'].create({
            'name': 'Premium Chair',
            'code': 'PC1',
        })
        
        name_get_result = chair.name_get()
        expected_name = "[PC1] Premium Chair"
        
        self.assertEqual(name_get_result[0][1], expected_name, "Chair name_get should include code and name")
        
    def test_barber_name_get(self):
        """Test barber name_get method"""
        barber = self.env['bp.barber.barber'].create({
            'name': 'Expert Barber',
            'barber_code': 'EB1',
        })
        
        name_get_result = barber.name_get()
        expected_name = "[EB1] Expert Barber"
        
        self.assertEqual(name_get_result[0][1], expected_name, "Barber name_get should include code and name")