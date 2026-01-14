# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestBarberManagementInstall(TransactionCase):
    """Smoke test to verify module installation"""
    
    def test_module_exists_after_install(self):
        """Test that the bp_barber_management module record exists after install"""
        module = self.env['ir.module.module'].search([
            ('name', '=', 'bp_barber_management')
        ])
        self.assertTrue(module, "bp_barber_management module should exist in ir.module.module")
        self.assertEqual(module.state, 'installed', "bp_barber_management module should be installed")