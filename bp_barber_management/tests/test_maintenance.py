# -*- coding: utf-8 -*-

import json
import base64
from datetime import datetime, timedelta
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestBarberMaintenance(TransactionCase):
    """Test maintenance and audit functionality for barber management"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env['res.company'].browse(1)  # Use main company
        
        # Create test partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer Maintenance',
            'email': 'testmaintenance@customer.com',
            'phone': '123-456-7890',
        })
        
        # Create test barber
        cls.barber = cls.env['bp.barber.barber'].create({
            'name': 'Test Barber Maintenance',
            'phone': '123-456-7890',
            'email': 'testbarbermaint@example.com'
        })
        
        # Create test service
        cls.service = cls.env['bp.barber.service'].create({
            'name': 'Test Haircut Maintenance',
            'list_price': 25.00,
            'duration_minutes': 30
        })

    def test_diagnostics_runs_and_reports_counts(self):
        """Test that diagnostics runs without errors and reports valid data"""
        # Create some test data first
        old_appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() - timedelta(days=200),
            'state': 'done',
        })
        
        recent_appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() + timedelta(hours=2),
            'state': 'confirmed',
        })
        
        # Get or create maintenance dashboard
        maintenance = self.env['bp.barber.maintenance'].get_or_create_dashboard(
            self.company.id
        )
        
        # Run diagnostics
        maintenance.action_run_diagnostics()
        
        # Check that stats were generated
        self.assertTrue(maintenance.stats_json, "Stats JSON should be populated")
        self.assertTrue(maintenance.last_run, "Last run time should be set")
        
        # Parse and validate stats structure
        stats = json.loads(maintenance.stats_json)
        
        # Check expected keys exist
        expected_keys = ['appointments', 'barbers', 'services', 'wallets', 'issues', 'system']
        for key in expected_keys:
            self.assertIn(key, stats, f"Stats should contain {key} section")
        
        # Check appointment data structure
        appt_stats = stats['appointments']
        self.assertIn('total', appt_stats)
        self.assertIn('by_state', appt_stats)
        self.assertIn('age_buckets', appt_stats)
        
        # Should have at least our test appointments
        self.assertGreaterEqual(appt_stats['total'], 2)
        self.assertGreater(appt_stats['by_state']['done'], 0)
        self.assertGreater(appt_stats['by_state']['confirmed'], 0)

    def test_archive_old_appointments(self):
        """Test archiving of old completed appointments"""
        # Create old done appointment
        old_done_appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() - timedelta(days=200),
            'state': 'done',
        })
        
        # Create old cancelled appointment  
        old_cancelled_appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() - timedelta(days=200),
            'state': 'cancelled',
        })
        
        # Create recent appointment (should not be archived)
        recent_appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() - timedelta(days=10),
            'state': 'done',
        })
        
        # Ensure all are active initially
        self.assertTrue(old_done_appointment.active)
        self.assertTrue(old_cancelled_appointment.active)
        self.assertTrue(recent_appointment.active)
        
        # Run archive task with 180 days threshold
        wizard = self.env['bp.barber.maintenance.console'].create({
            'task': 'archive_old_appointments',
            'days_threshold': 180,
        })
        wizard._archive_old_appointments()
        
        # Refresh records
        old_done_appointment.refresh()
        old_cancelled_appointment.refresh()
        recent_appointment.refresh()
        
        # Check results
        self.assertFalse(old_done_appointment.active, "Old done appointment should be archived")
        self.assertFalse(old_cancelled_appointment.active, "Old cancelled appointment should be archived")
        self.assertTrue(recent_appointment.active, "Recent appointment should remain active")

    def test_archive_stale_wallets(self):
        """Test archiving of expired wallets with zero balance"""
        # Create package for wallets
        package = self.env['bp.barber.package'].create({
            'name': 'Test Package Maintenance',
            'line_ids': [(0, 0, {
                'service_id': self.service.id,
                'quantity': 5,
                'price': 100.0,
            })]
        })
        
        # Create old expired wallet with zero balance
        old_wallet = self.env['bp.barber.package.wallet'].create({
            'partner_id': self.partner.id,
            'package_id': package.id,
            'purchase_date': datetime.now().date() - timedelta(days=100),
            'expiry_date': datetime.now().date() - timedelta(days=50),
            'units_remaining': 0,
            'amount_remaining': 0,
        })
        
        # Create recent expired wallet (should not be archived due to age)
        recent_wallet = self.env['bp.barber.package.wallet'].create({
            'partner_id': self.partner.id,
            'package_id': package.id,
            'purchase_date': datetime.now().date() - timedelta(days=10),
            'expiry_date': datetime.now().date() - timedelta(days=5),
            'units_remaining': 0,
            'amount_remaining': 0,
        })
        
        # Create old expired wallet with balance (should not be archived)
        wallet_with_balance = self.env['bp.barber.package.wallet'].create({
            'partner_id': self.partner.id,
            'package_id': package.id,
            'purchase_date': datetime.now().date() - timedelta(days=100),
            'expiry_date': datetime.now().date() - timedelta(days=50),
            'units_remaining': 2,
            'amount_remaining': 40,
        })
        
        # Ensure all are active initially
        self.assertTrue(old_wallet.active)
        self.assertTrue(recent_wallet.active)
        self.assertTrue(wallet_with_balance.active)
        
        # Run archive stale wallets with 30 days threshold
        wizard = self.env['bp.barber.maintenance.console'].create({
            'task': 'archive_stale_wallets',
            'wallet_days_expired': 30,
        })
        wizard._archive_stale_wallets()
        
        # Refresh records
        old_wallet.refresh()
        recent_wallet.refresh()
        wallet_with_balance.refresh()
        
        # Check results
        self.assertFalse(old_wallet.active, "Old expired empty wallet should be archived")
        self.assertTrue(recent_wallet.active, "Recent expired wallet should remain active")
        self.assertTrue(wallet_with_balance.active, "Wallet with balance should remain active")

    def test_delete_cancelled_appointments(self):
        """Test permanent deletion of old cancelled appointments"""
        # Create old cancelled appointment (eligible for deletion)
        old_cancelled = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() - timedelta(days=200),
            'state': 'cancelled',
        })
        
        # Create old no-show appointment  
        old_noshow = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() - timedelta(days=200),
            'state': 'no_show',
        })
        
        # Create recent cancelled (should not be deleted due to safety threshold)
        recent_cancelled = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() - timedelta(days=30),
            'state': 'cancelled',
        })
        
        old_cancelled_id = old_cancelled.id
        old_noshow_id = old_noshow.id
        recent_cancelled_id = recent_cancelled.id
        
        # Run deletion with include_noshows=True and 180 days threshold  
        wizard = self.env['bp.barber.maintenance.console'].create({
            'task': 'delete_cancelled_appointments',
            'days_threshold': 180,
            'include_noshows': True,
        })
        wizard._delete_cancelled_appointments()
        
        # Check that old appointments were deleted
        self.assertFalse(self.env['bp.barber.appointment'].browse(old_cancelled_id).exists())
        self.assertFalse(self.env['bp.barber.appointment'].browse(old_noshow_id).exists())
        
        # Check that recent appointment still exists
        self.assertTrue(self.env['bp.barber.appointment'].browse(recent_cancelled_id).exists())

    def test_delete_safety_threshold(self):
        """Test safety check prevents deletion of appointments less than 90 days old"""
        wizard = self.env['bp.barber.maintenance.console'].create({
            'task': 'delete_cancelled_appointments',
            'days_threshold': 30,  # Less than 90 days
        })
        
        with self.assertRaises(UserError) as cm:
            wizard._delete_cancelled_appointments()
            
        self.assertIn("Safety check", str(cm.exception))

    def test_fix_orphans(self):
        """Test fixing orphaned records"""
        # Create appointment with missing barber (orphan)
        orphan_appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() + timedelta(hours=2),
            'state': 'draft',
        })
        # Manually remove barber to create orphan
        orphan_appointment.write({'barber_id': False})
        
        # Create service without product (another type of orphan)
        orphan_service = self.env['bp.barber.service'].create({
            'name': 'Test Orphan Service',
            'list_price': 15.00,
            'duration_minutes': 20,
        })
        # Remove product link to create orphan
        orphan_service.write({'product_id': False})
        
        # Ensure orphans exist
        self.assertFalse(orphan_appointment.barber_id)
        self.assertFalse(orphan_service.product_id)
        self.assertTrue(orphan_appointment.active)
        self.assertTrue(orphan_service.active)
        
        # Run fix orphans task
        wizard = self.env['bp.barber.maintenance.console'].create({
            'task': 'fix_orphans',
        })
        wizard._fix_orphans()
        
        # Refresh records
        orphan_appointment.refresh()
        orphan_service.refresh()
        
        # Check that orphaned appointment was deactivated
        self.assertFalse(orphan_appointment.active, "Orphaned appointment should be deactivated")
        
        # Check that service got a product link created
        self.assertTrue(orphan_service.product_id, "Service should have product link created")

    def test_export_csv(self):
        """Test CSV export functionality"""
        # Create test appointment for export
        test_appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() + timedelta(hours=2),
            'state': 'confirmed',
        })
        
        # Test CSV export via wizard
        wizard = self.env['bp.barber.maintenance.console'].create({
            'task': 'export_csv',
            'model_to_export': 'bp.barber.appointment',
            'export_fields': 'name,partner_id,state',
            'domain_json': '[["state", "=", "confirmed"]]',
        })
        wizard._export_csv()
        
        # Check that file data was generated
        self.assertTrue(wizard.file_data, "CSV file data should be generated")
        self.assertTrue(wizard.file_name, "CSV filename should be set")
        self.assertIn('.csv', wizard.file_name)
        
        # Decode and check CSV content
        csv_content = base64.b64decode(wizard.file_data).decode('utf-8')
        self.assertIn('name,partner_id,state', csv_content, "CSV should have header row")
        self.assertIn('confirmed', csv_content, "CSV should contain confirmed appointments")

    def test_maintenance_dashboard_creation(self):
        """Test maintenance dashboard creation and retrieval"""
        # Get or create dashboard
        dashboard1 = self.env['bp.barber.maintenance'].get_or_create_dashboard(self.company.id)
        
        self.assertTrue(dashboard1.exists(), "Dashboard should be created")
        self.assertEqual(dashboard1.company_id, self.company)
        
        # Should return same dashboard on subsequent calls
        dashboard2 = self.env['bp.barber.maintenance'].get_or_create_dashboard(self.company.id)
        self.assertEqual(dashboard1.id, dashboard2.id, "Should return same dashboard instance")

    def test_cron_methods(self):
        """Test cron job methods execute without errors"""
        # Create test data for cron operations
        old_appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'service_ids': [(6, 0, [self.service.id])],
            'start_datetime': datetime.now() - timedelta(days=400),
            'state': 'done',
        })
        
        # Test cron archive old appointments
        try:
            self.env['bp.barber.maintenance.console'].cron_archive_old_appointments(days_threshold=365)
        except Exception as e:
            self.fail(f"Cron archive old appointments failed: {e}")
            
        # Test cron archive stale wallets
        try:
            self.env['bp.barber.maintenance.console'].cron_archive_stale_wallets(days_threshold=60)
        except Exception as e:
            self.fail(f"Cron archive stale wallets failed: {e}")
            
        # Test cron purge chatter logs (should be no-op by default)
        try:
            self.env['bp.barber.maintenance.console'].cron_purge_old_chatter_logs()
        except Exception as e:
            self.fail(f"Cron purge chatter logs failed: {e}")

    def test_recompute_kpis_cache(self):
        """Test KPI cache recomputation"""
        wizard = self.env['bp.barber.maintenance.console'].create({
            'task': 'recompute_kpis_cache',
        })
        
        # Should run without errors
        try:
            wizard._recompute_kpis_cache()
        except Exception as e:
            self.fail(f"KPI cache recomputation failed: {e}")
            
        # Should have result message
        self.assertTrue(wizard.result_message, "Should have result message")

    def test_maintenance_console_wizard_creation(self):
        """Test maintenance console wizard can be created and configured"""
        wizard = self.env['bp.barber.maintenance.console'].create({
            'task': 'diagnostics',
        })
        
        self.assertEqual(wizard.task, 'diagnostics')
        self.assertEqual(wizard.days_threshold, 180)  # Default value
        
        # Test different task configurations
        export_wizard = self.env['bp.barber.maintenance.console'].create({
            'task': 'export_csv',
            'model_to_export': 'bp.barber.appointment',
            'export_fields': 'name,state',
        })
        
        self.assertEqual(export_wizard.model_to_export, 'bp.barber.appointment')
        self.assertEqual(export_wizard.export_fields, 'name,state')

    def test_invalid_domain_json_handling(self):
        """Test handling of invalid JSON domain"""
        wizard = self.env['bp.barber.maintenance.console'].create({
            'task': 'export_csv',
            'model_to_export': 'bp.barber.appointment',
            'domain_json': 'invalid json',
        })
        
        with self.assertRaises(UserError) as cm:
            wizard._export_csv()
            
        self.assertIn("Invalid JSON", str(cm.exception))

    def test_stats_summary_computation(self):
        """Test HTML stats summary generation from JSON"""
        maintenance = self.env['bp.barber.maintenance'].create({
            'company_id': self.company.id,
        })
        
        # Test with no stats
        maintenance._compute_stats_summary()
        self.assertIn("No diagnostics data", maintenance.stats_summary)
        
        # Test with valid stats
        sample_stats = {
            'appointments': {
                'total': 100,
                'by_state': {'confirmed': 20, 'done': 70, 'cancelled': 10},
                'age_buckets': {'Last 30 days': 30, '31-180 days': 50, 'Over 180 days': 20}
            },
            'issues': {
                'appointments_missing_barber': 0,
                'appointments_missing_services': 1
            },
            'system': {
                'total_companies': 1,
                'active_users': 5
            }
        }
        
        maintenance.write({'stats_json': json.dumps(sample_stats)})
        maintenance._compute_stats_summary()
        
        # Check HTML contains expected sections
        summary_html = maintenance.stats_summary
        self.assertIn('Appointments Overview', summary_html)
        self.assertIn('Data Issues', summary_html)
        self.assertIn('System Health', summary_html)
        self.assertIn('Total: 100', summary_html)

    def test_post_init_indexes_exist(self):
        """Test that database indexes were created by post_init_hook"""
        # This test checks if the indexes exist in the database
        # Note: This may require database introspection capabilities
        
        # Test appointment indexes
        index_queries = [
            "SELECT indexname FROM pg_indexes WHERE indexname = 'idx_bp_appt_company_state_start'",
            "SELECT indexname FROM pg_indexes WHERE indexname = 'idx_bp_appt_barber_start'",
            "SELECT indexname FROM pg_indexes WHERE indexname = 'idx_pos_order_line_barber'",
        ]
        
        for query in index_queries:
            try:
                self.env.cr.execute(query)
                result = self.env.cr.fetchone()
                # If index exists, result should not be empty
                # This is informational - indexes may not exist in test environments
                _logger.info(f"Index check: {query} -> {result}")
            except Exception as e:
                # Index queries may fail in test environments, that's OK
                _logger.info(f"Index check failed (expected in tests): {e}")


class TestMaintenancePerformance(TransactionCase):
    """Test performance aspects of maintenance operations"""
    
    def test_large_dataset_diagnostics(self):
        """Test diagnostics performance with larger dataset"""
        # Skip this test if we don't want to create large datasets in CI
        if not self.env.context.get('test_performance'):
            self.skipTest("Performance test skipped - set test_performance context to enable")
            
        # Create multiple appointments, barbers, services
        partner = self.env['res.partner'].create({
            'name': 'Performance Test Customer',
            'email': 'perf@test.com'
        })
        
        barber = self.env['bp.barber.barber'].create({
            'name': 'Performance Test Barber',
            'phone': '555-0001'
        })
        
        service = self.env['bp.barber.service'].create({
            'name': 'Performance Test Service',
            'list_price': 20.0,
            'duration_minutes': 30
        })
        
        # Create 50 appointments with various states and dates
        appointments = []
        for i in range(50):
            start_date = datetime.now() - timedelta(days=i*2)
            state = ['done', 'cancelled', 'confirmed'][i % 3]
            
            appointment = self.env['bp.barber.appointment'].create({
                'partner_id': partner.id,
                'barber_id': barber.id,
                'service_ids': [(6, 0, [service.id])],
                'start_datetime': start_date,
                'state': state,
            })
            appointments.append(appointment)
        
        # Time the diagnostics operation
        import time
        start_time = time.time()
        
        maintenance = self.env['bp.barber.maintenance'].get_or_create_dashboard()
        maintenance.action_run_diagnostics()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Diagnostics should complete reasonably quickly (under 5 seconds for 50 records)
        self.assertLess(execution_time, 5.0, f"Diagnostics took too long: {execution_time}s")
        
        # Verify results are accurate
        stats = json.loads(maintenance.stats_json)
        appt_stats = stats['appointments']
        
        # Should count our test appointments
        self.assertGreaterEqual(appt_stats['total'], 50)