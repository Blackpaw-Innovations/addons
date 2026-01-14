# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from datetime import datetime, timedelta
import base64


class TestAppointmentReport(TransactionCase):
    """Test suite for appointment visit summary report"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test data
        cls.company = cls.env.company
        
        # Create test barber
        cls.barber = cls.env['bp.barber.barber'].create({
            'name': 'Test Barber',
            'phone': '+1234567890',
            'color_index': 1,
        })
        
        # Create test chair
        cls.chair = cls.env['bp.barber.chair'].create({
            'name': 'Chair 1',
            'is_active': True,
        })
        
        # Create test services
        cls.service1 = cls.env['bp.service'].create({
            'name': 'Haircut',
            'duration_minutes': 30,
            'list_price': 25.0,
        })
        
        cls.service2 = cls.env['bp.service'].create({
            'name': 'Beard Trim',
            'duration_minutes': 15,
            'list_price': 15.0,
        })
        
        # Create test customer
        cls.customer = cls.env['res.partner'].create({
            'name': 'John Customer',
            'phone': '+1987654321',
            'email': 'john@example.com'
        })
        
        # Create currency if needed
        cls.currency = cls.env.ref('base.USD')

    def test_report_renders_pdf(self):
        """Test that the visit summary report renders to PDF without errors"""
        
        # Create test appointment
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.customer.id,
            'phone': self.customer.phone,
            'email': self.customer.email,
            'barber_id': self.barber.id,
            'chair_id': self.chair.id,
            'start_datetime': datetime.now() + timedelta(hours=1),
            'service_ids': [(6, 0, [self.service1.id, self.service2.id])],
            'note': 'Test appointment notes for report generation',
        })
        
        # Confirm appointment
        appointment.action_confirm()
        
        # Get report reference
        report = self.env.ref('bp_barber_management.action_report_bp_appointment_visit')
        
        # Render the report
        pdf_bytes, fmt = report._render_qweb_pdf([appointment.id])
        
        # Assertions
        self.assertEqual(fmt, 'pdf', "Report should render as PDF format")
        self.assertGreater(len(pdf_bytes), 0, "PDF should contain data")
        self.assertTrue(pdf_bytes.startswith(b'%PDF'), "Output should be valid PDF")

    def test_print_button_action(self):
        """Test that the print visit summary action returns correct report data"""
        
        # Create test appointment
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.customer.id,
            'phone': self.customer.phone,
            'email': self.customer.email,
            'barber_id': self.barber.id,
            'start_datetime': datetime.now() + timedelta(hours=1),
            'service_ids': [(6, 0, [self.service1.id])],
            'state': 'done'
        })
        
        # Call the print action
        result = appointment.action_print_visit_summary()
        
        # Verify return structure
        self.assertIsInstance(result, dict, "Should return dictionary")
        self.assertEqual(result.get('type'), 'ir.actions.report', "Should return report action")
        self.assertEqual(
            result.get('report_name'), 
            'bp_barber_management.report_appointment_visit',
            "Should reference correct report template"
        )

    def test_report_with_multiple_services(self):
        """Test report rendering with multiple services"""
        
        # Create appointment with multiple services
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.customer.id,
            'phone': self.customer.phone,
            'email': self.customer.email,
            'barber_id': self.barber.id,
            'chair_id': self.chair.id,
            'start_datetime': datetime.now() + timedelta(hours=1),
            'service_ids': [(6, 0, [self.service1.id, self.service2.id])],
            'discount_percent': 10.0,
            'note': 'Multi-service appointment with discount',
            'state': 'done'
        })
        
        # Verify computed totals
        expected_subtotal = self.service1.list_price + self.service2.list_price
        self.assertEqual(appointment.price_subtotal, expected_subtotal)
        
        expected_total = expected_subtotal * 0.9  # 10% discount
        self.assertEqual(appointment.price_total, expected_total)
        
        # Render report
        report = self.env.ref('bp_barber_management.action_report_bp_appointment_visit')
        pdf_bytes, fmt = report._render_qweb_pdf([appointment.id])
        
        # Should render successfully
        self.assertEqual(fmt, 'pdf')
        self.assertGreater(len(pdf_bytes), 0)

    def test_report_without_optional_fields(self):
        """Test report rendering when optional fields are empty"""
        
        # Create minimal appointment
        appointment = self.env['bp.barber.appointment'].create({
            'start_datetime': datetime.now() + timedelta(hours=1),
            'service_ids': [(6, 0, [self.service1.id])],
            'state': 'confirmed'
        })
        
        # Should render even without customer, barber, chair, notes
        report = self.env.ref('bp_barber_management.action_report_bp_appointment_visit')
        pdf_bytes, fmt = report._render_qweb_pdf([appointment.id])
        
        self.assertEqual(fmt, 'pdf')
        self.assertGreater(len(pdf_bytes), 0)

    def test_report_accessibility_from_different_states(self):
        """Test that report is accessible from correct appointment states"""
        
        # Create appointment
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.customer.id,
            'barber_id': self.barber.id,
            'start_datetime': datetime.now() + timedelta(hours=1),
            'service_ids': [(6, 0, [self.service1.id])],
        })
        
        # Draft state - should not be able to print (button invisible)
        self.assertEqual(appointment.state, 'draft')
        
        # Confirmed state - should be able to print
        appointment.action_confirm()
        self.assertEqual(appointment.state, 'confirmed')
        result = appointment.action_print_visit_summary()
        self.assertEqual(result.get('type'), 'ir.actions.report')
        
        # In service state - should be able to print
        appointment.action_start_service()
        self.assertEqual(appointment.state, 'in_service')
        result = appointment.action_print_visit_summary()
        self.assertEqual(result.get('type'), 'ir.actions.report')
        
        # Done state - should be able to print
        appointment.action_finish_service()
        self.assertEqual(appointment.state, 'done')
        result = appointment.action_print_visit_summary()
        self.assertEqual(result.get('type'), 'ir.actions.report')

    def test_report_paperformat_configuration(self):
        """Test that report uses correct paper format"""
        
        # Get report and paperformat
        report = self.env.ref('bp_barber_management.action_report_bp_appointment_visit')
        paperformat = self.env.ref('bp_barber_management.paperformat_barber_visit')
        
        # Verify report is linked to paperformat
        self.assertEqual(report.paperformat_id, paperformat)
        
        # Verify paperformat configuration
        self.assertEqual(paperformat.format, 'A4')
        self.assertEqual(paperformat.orientation, 'Portrait')
        self.assertLessEqual(paperformat.margin_top, 50)
        self.assertLessEqual(paperformat.margin_bottom, 30)

    def test_report_filename_generation(self):
        """Test that report generates proper filename"""
        
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.customer.id,
            'start_datetime': datetime.now() + timedelta(hours=1),
            'service_ids': [(6, 0, [self.service1.id])],
        })
        
        # Get report
        report = self.env.ref('bp_barber_management.action_report_bp_appointment_visit')
        
        # Check print report name expression
        expected_filename = f"Visit_{appointment.name}"
        # The actual evaluation happens during report generation
        # Here we just verify the template is set correctly
        self.assertEqual(report.print_report_name, "'Visit_%s' % (object.name or '')")

    def test_multicompany_context(self):
        """Test report respects multi-company context"""
        
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.customer.id,
            'barber_id': self.barber.id,
            'start_datetime': datetime.now() + timedelta(hours=1),
            'service_ids': [(6, 0, [self.service1.id])],
            'company_id': self.company.id,
            'state': 'confirmed'
        })
        
        # Render report
        report = self.env.ref('bp_barber_management.action_report_bp_appointment_visit')
        pdf_bytes, fmt = report._render_qweb_pdf([appointment.id])
        
        # Should render successfully with company context
        self.assertEqual(fmt, 'pdf')
        self.assertGreater(len(pdf_bytes), 0)
        
        # Verify appointment belongs to correct company
        self.assertEqual(appointment.company_id, self.company)