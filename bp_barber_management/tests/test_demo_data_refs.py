# -*- coding: utf-8 -*-

from odoo.tests.common import tagged, TransactionCase
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestDemoDataRefs(TransactionCase):
    """Test that demo data references are valid and properly linked"""

    def test_demo_services_exist_and_linked(self):
        """Test that demo services exist and have linked POS products"""
        
        # Check that all demo services exist
        services = self.env['bp.service'].search([
            ('code', 'in', ['CUT', 'SHV', 'CNS', 'BRD', 'KID'])
        ])
        
        self.assertEqual(len(services), 5, "All 5 demo services should exist")
        
        # Verify service details
        service_data = {
            'CUT': {'name': 'Haircut', 'price': 10.0, 'duration': 30},
            'SHV': {'name': 'Shave', 'price': 6.0, 'duration': 20},
            'CNS': {'name': 'Cut + Shave', 'price': 15.0, 'duration': 50},
            'BRD': {'name': 'Beard Trim', 'price': 7.0, 'duration': 20},
            'KID': {'name': 'Kids Cut', 'price': 8.0, 'duration': 25},
        }
        
        for service in services:
            expected = service_data[service.code]
            self.assertEqual(service.name, expected['name'])
            self.assertEqual(service.list_price, expected['price'])
            self.assertEqual(service.duration_minutes, expected['duration'])
            
            # Check that POS product is auto-created
            pos_product = self.env['product.product'].search([
                ('name', '=', service.name),
                ('type', '=', 'service'),
                ('available_in_pos', '=', True)
            ])
            self.assertTrue(pos_product, f"POS product should exist for service {service.name}")

    def test_demo_barbers_and_chairs_linked(self):
        """Test that demo barbers and chairs exist and are properly linked"""
        
        # Check chairs
        chairs = self.env['bp.barber.chair'].search([
            ('code', 'in', ['C1', 'C2'])
        ])
        self.assertEqual(len(chairs), 2, "Both demo chairs should exist")
        
        chair_1 = chairs.filtered(lambda c: c.code == 'C1')
        chair_2 = chairs.filtered(lambda c: c.code == 'C2')
        
        self.assertEqual(chair_1.name, 'Chair 1')
        self.assertEqual(chair_2.name, 'Chair 2')
        self.assertTrue(chair_1.is_available)
        self.assertTrue(chair_2.is_available)
        
        # Check barbers
        barbers = self.env['bp.barber.barber'].search([
            ('barber_code', 'in', ['JBN', 'MRS', 'ALX'])
        ])
        self.assertEqual(len(barbers), 3, "All 3 demo barbers should exist")
        
        john = barbers.filtered(lambda b: b.barber_code == 'JBN')
        mary = barbers.filtered(lambda b: b.barber_code == 'MRS')
        alex = barbers.filtered(lambda b: b.barber_code == 'ALX')
        
        # Verify barber details
        self.assertEqual(john.name, 'John Barber')
        self.assertEqual(john.skill_level, 'senior')
        self.assertEqual(john.chair_id, chair_1)
        
        self.assertEqual(mary.name, 'Mary Stylist')
        self.assertEqual(mary.skill_level, 'mid')
        self.assertEqual(mary.chair_id, chair_2)
        
        self.assertEqual(alex.name, 'Alex Fade')
        self.assertEqual(alex.skill_level, 'junior')
        self.assertFalse(alex.chair_id, "Alex should have no chair assigned (null case)")

    def test_demo_schedules_exist(self):
        """Test that schedules exist for John and Mary Monday-Saturday"""
        
        john = self.env.ref('bp_barber_management.bp_barber_john')
        mary = self.env.ref('bp_barber_management.bp_barber_mary')
        
        # Check John's schedules (Mon-Sat, weekday 0-5)
        john_schedules = self.env['bp.barber.schedule'].search([
            ('barber_id', '=', john.id)
        ])
        self.assertEqual(len(john_schedules), 6, "John should have 6 schedule entries (Mon-Sat)")
        
        weekdays = john_schedules.mapped('weekday')
        self.assertEqual(set(weekdays), {0, 1, 2, 3, 4, 5}, "John should have Mon-Sat schedules")
        
        for schedule in john_schedules:
            self.assertEqual(schedule.start_time, 9.0, "Start time should be 09:00")
            self.assertEqual(schedule.end_time, 18.0, "End time should be 18:00")
            self.assertTrue(schedule.active, "Schedule should be active")
        
        # Check Mary's schedules
        mary_schedules = self.env['bp.barber.schedule'].search([
            ('barber_id', '=', mary.id)
        ])
        self.assertEqual(len(mary_schedules), 6, "Mary should have 6 schedule entries (Mon-Sat)")
        
        weekdays = mary_schedules.mapped('weekday')
        self.assertEqual(set(weekdays), {0, 1, 2, 3, 4, 5}, "Mary should have Mon-Sat schedules")

    def test_demo_appointments_exist_with_expected_states(self):
        """Test that demo appointments exist with correct states and data"""
        
        # Get demo appointments
        confirmed_apt = self.env.ref('bp_barber_management.bp_appointment_confirmed')
        draft_apt = self.env.ref('bp_barber_management.bp_appointment_draft')
        in_service_apt = self.env.ref('bp_barber_management.bp_appointment_in_service')
        
        # Verify states
        self.assertEqual(confirmed_apt.state, 'confirmed')
        self.assertEqual(draft_apt.state, 'draft')
        self.assertEqual(in_service_apt.state, 'in_service')
        
        # Verify barber assignments
        mary = self.env.ref('bp_barber_management.bp_barber_mary')
        john = self.env.ref('bp_barber_management.bp_barber_john')
        
        self.assertEqual(confirmed_apt.barber_id, mary)
        self.assertEqual(draft_apt.barber_id, john)
        self.assertEqual(in_service_apt.barber_id, john)
        
        # Verify services are linked
        self.assertTrue(confirmed_apt.service_ids, "Confirmed appointment should have services")
        self.assertTrue(draft_apt.service_ids, "Draft appointment should have services")
        self.assertTrue(in_service_apt.service_ids, "In-service appointment should have services")

    def test_retail_products_exist_and_pos_available(self):
        """Test that retail products (perfumes & shoes) exist and are POS-available"""
        
        # Check perfume products
        perfumes = self.env['product.product'].search([
            ('name', 'in', ['Cedar Woods 50ml', 'Ocean Mist 100ml', 'Amber Night 50ml'])
        ])
        self.assertEqual(len(perfumes), 3, "All 3 perfume products should exist")
        
        for perfume in perfumes:
            self.assertEqual(perfume.type, 'product', "Perfumes should be storable products")
            self.assertTrue(perfume.available_in_pos, "Perfumes should be available in POS")
            self.assertTrue(perfume.sale_ok, "Perfumes should be saleable")
        
        # Check shoe template and variants
        shoe_template = self.env['product.template'].search([
            ('name', '=', 'Casual Sneaker')
        ])
        self.assertEqual(len(shoe_template), 1, "Shoe template should exist")
        
        shoe_variants = shoe_template.product_variant_ids
        self.assertGreater(len(shoe_variants), 1, "Shoe variants should be generated")
        
        # Check that at least some variants have size and color attributes
        for variant in shoe_variants:
            self.assertTrue(variant.available_in_pos, "Shoe variants should be available in POS")
        
        # Verify attributes exist
        size_attr = self.env['product.attribute'].search([('name', '=', 'Size')])
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')])
        
        self.assertTrue(size_attr, "Size attribute should exist")
        self.assertTrue(color_attr, "Color attribute should exist")
        
        # Check attribute values
        size_values = size_attr.value_ids.mapped('name')
        color_values = color_attr.value_ids.mapped('name')
        
        self.assertTrue({'39', '40', '41', '42', '43'}.issubset(set(size_values)), 
                       "All size values should exist")
        self.assertTrue({'Black', 'White'}.issubset(set(color_values)), 
                       "All color values should exist")

    def test_pos_config_demo_exists(self):
        """Test that demo POS config exists with proper barber settings"""
        
        pos_config = self.env.ref('bp_barber_management.bp_pos_config_front_desk')
        
        self.assertEqual(pos_config.name, 'Barber Front Desk')
        self.assertTrue(pos_config.enable_barber_mode, "Barber mode should be enabled")
        self.assertTrue(pos_config.pos_autocomplete_appointment, "Auto-complete should be enabled")
        self.assertEqual(pos_config.pos_appointments_scope, 'all_barbers')
        
        # Verify default barber is set
        john = self.env.ref('bp_barber_management.bp_barber_john')
        self.assertEqual(pos_config.pos_barber_default, john)

    def test_demo_data_multicompany_compliance(self):
        """Test that demo data respects multi-company setup"""
        
        current_company = self.env.company
        
        # Check that barbers belong to current company
        barbers = self.env['bp.barber.barber'].search([
            ('barber_code', 'in', ['JBN', 'MRS', 'ALX'])
        ])
        
        for barber in barbers:
            # Company field might be implicit or explicit
            if hasattr(barber, 'company_id') and barber.company_id:
                self.assertEqual(barber.company_id, current_company)
        
        # Check appointments
        appointments = self.env['bp.barber.appointment'].search([
            ('id', 'in', [
                self.env.ref('bp_barber_management.bp_appointment_confirmed').id,
                self.env.ref('bp_barber_management.bp_appointment_draft').id,
                self.env.ref('bp_barber_management.bp_appointment_in_service').id,
            ])
        ])
        
        for appointment in appointments:
            if hasattr(appointment, 'company_id') and appointment.company_id:
                self.assertEqual(appointment.company_id, current_company)