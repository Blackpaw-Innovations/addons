# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
from unittest.mock import patch


class TestPackages(TransactionCase):

    def setUp(self):
        super().setUp()
        
        # Create test company and currency
        self.company = self.env.company
        self.currency = self.company.currency_id
        
        # Create test partner
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@example.com',
        })
        
        # Create test services
        self.haircut_service = self.env['bp.barber.service'].create({
            'name': 'Haircut',
            'duration_minutes': 30,
            'price': 50.0,
        })
        
        self.shave_service = self.env['bp.barber.service'].create({
            'name': 'Shave',
            'duration_minutes': 15,
            'price': 25.0,
        })
        
        # Create test barber
        self.barber = self.env['bp.barber.barber'].create({
            'name': 'Test Barber',
            'email': 'barber@example.com',
        })

    def test_purchase_value_package_creates_wallet(self):
        """Test that purchasing a value package creates a wallet with correct balance"""
        # Create value package
        package = self.env['bp.barber.package'].create({
            'name': 'Store Credit 1000',
            'code': 'CREDIT1000',
            'package_type': 'value',
            'value_amount': 1000.0,
        })
        
        # Verify POS product was auto-created
        self.assertTrue(package.pos_product_id)
        self.assertEqual(package.pos_product_id.list_price, 1000.0)
        
        # Create mock POS order line
        pos_order = self.env['pos.order'].create({
            'name': 'Test Order',
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': datetime.now(),
        })
        
        pos_order_line = self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': package.pos_product_id.id,
            'qty': 1,
            'price_unit': 1000.0,
            'price_subtotal_incl': 1000.0,
        })
        
        # Create wallet from sale
        wallet = self.env['bp.barber.package.wallet'].credit_from_sale(
            self.env, pos_order_line
        )
        
        # Verify wallet was created correctly
        self.assertTrue(wallet)
        self.assertEqual(wallet.partner_id, self.partner)
        self.assertEqual(wallet.package_id, package)
        self.assertEqual(wallet.balance_amount, 1000.0)
        
        # Verify wallet line was created
        wallet_lines = wallet.wallet_line_ids
        self.assertEqual(len(wallet_lines), 1)
        self.assertEqual(wallet_lines[0].move_type, 'credit')
        self.assertEqual(wallet_lines[0].amount, 1000.0)

    def test_purchase_qty_package_creates_units(self):
        """Test that purchasing a quantity package creates service units"""
        # Create qty package (5 Haircuts)
        package = self.env['bp.barber.package'].create({
            'name': 'Haircut x5',
            'code': 'HAIRCUT5',
            'package_type': 'qty',
        })
        
        # Add package line
        self.env['bp.barber.package.line'].create({
            'package_id': package.id,
            'service_id': self.haircut_service.id,
            'qty': 5.0,
        })
        
        # Create mock POS order line
        pos_order = self.env['pos.order'].create({
            'name': 'Test Order',
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': datetime.now(),
        })
        
        pos_order_line = self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': package.pos_product_id.id,
            'qty': 1,
            'price_unit': 250.0,
            'price_subtotal_incl': 250.0,
        })
        
        # Create wallet from sale
        wallet = self.env['bp.barber.package.wallet'].credit_from_sale(
            self.env, pos_order_line
        )
        
        # Verify units are available
        available_units = wallet.get_available_units(self.haircut_service)
        self.assertEqual(available_units, 5.0)
        
        # Verify wallet lines were created
        wallet_lines = wallet.wallet_line_ids
        self.assertEqual(len(wallet_lines), 1)
        self.assertEqual(wallet_lines[0].move_type, 'credit')
        self.assertEqual(wallet_lines[0].service_id, self.haircut_service)
        self.assertEqual(wallet_lines[0].qty, 5.0)

    def test_redeem_on_appointment_without_pos(self):
        """Test redemption when appointment is finished without POS order"""
        # Create package and wallet with units
        package = self.env['bp.barber.package'].create({
            'name': 'Haircut x3',
            'code': 'HAIRCUT3',
            'package_type': 'qty',
        })
        
        self.env['bp.barber.package.line'].create({
            'package_id': package.id,
            'service_id': self.haircut_service.id,
            'qty': 3.0,
        })
        
        wallet = self.env['bp.barber.package.wallet'].create({
            'partner_id': self.partner.id,
            'package_id': package.id,
            'purchase_date': date.today(),
        })
        
        # Credit the wallet with units
        wallet._create_wallet_line(
            move_type='credit',
            service_id=self.haircut_service.id,
            qty=3.0,
            note="Initial credit"
        )
        
        # Create appointment
        appointment = self.env['bp.barber.appointment'].create({
            'name': 'Test Appointment',
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
            'start_datetime': datetime.now(),
            'service_ids': [(6, 0, [self.haircut_service.id])],
            'state': 'in_service',
        })
        
        # Finish appointment (should trigger package redemption)
        appointment.action_finish_service()
        
        # Verify units were consumed
        remaining_units = wallet.get_available_units(self.haircut_service)
        self.assertEqual(remaining_units, 2.0)  # 3 - 1 = 2
        
        # Verify redemption record was created
        redemptions = self.env['bp.barber.package.redemption'].search([
            ('wallet_id', '=', wallet.id),
            ('appointment_id', '=', appointment.id)
        ])
        self.assertEqual(len(redemptions), 1)
        self.assertEqual(redemptions[0].qty, 1.0)
        self.assertEqual(redemptions[0].service_id, self.haircut_service)

    def test_pos_redemption_reduces_due(self):
        """Test that POS redemption reduces amount due correctly"""
        # Create value wallet with 1000 credit
        package = self.env['bp.barber.package'].create({
            'name': 'Store Credit 1000',
            'code': 'CREDIT1000',
            'package_type': 'value',
            'value_amount': 1000.0,
        })
        
        wallet = self.env['bp.barber.package.wallet'].create({
            'partner_id': self.partner.id,
            'package_id': package.id,
            'purchase_date': date.today(),
        })
        
        # Credit wallet with 1000
        wallet._create_wallet_line(
            move_type='credit',
            amount=1000.0,
            note="Initial credit"
        )
        
        # Create POS order with total 600
        pos_order = self.env['pos.order'].create({
            'name': 'Test Order',
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'date_order': datetime.now(),
            'package_redemptions_data': '[{"wallet_id": %d, "amount": 600.0}]' % wallet.id,
        })
        
        pos_order_line = self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': self.haircut_service.product_id.id,
            'qty': 12,  # 12 * 50 = 600
            'price_unit': 50.0,
            'price_subtotal_incl': 600.0,
        })
        
        # Process package redemptions
        pos_order._process_package_redemptions(pos_order)
        
        # Verify wallet balance was reduced
        wallet._compute_balances()  # Recompute to get latest
        self.assertEqual(wallet.balance_amount, 400.0)  # 1000 - 600 = 400
        
        # Verify redemption record exists
        redemptions = self.env['bp.barber.package.redemption'].search([
            ('wallet_id', '=', wallet.id),
            ('pos_order_line_id', '=', pos_order_line.id)
        ])
        self.assertEqual(len(redemptions), 1)
        self.assertEqual(redemptions[0].amount, 600.0)

    def test_expiry_blocks_redemption(self):
        """Test that expired wallets cannot be redeemed"""
        # Create package with 1 day validity
        package = self.env['bp.barber.package'].create({
            'name': 'Expired Package',
            'code': 'EXPIRED',
            'package_type': 'value',
            'value_amount': 100.0,
            'duration_days': 1,
        })
        
        # Create wallet with past purchase date
        wallet = self.env['bp.barber.package.wallet'].create({
            'partner_id': self.partner.id,
            'package_id': package.id,
            'purchase_date': date.today() - timedelta(days=5),  # 5 days ago
        })
        
        # Credit wallet
        wallet._create_wallet_line(
            move_type='credit',
            amount=100.0,
            note="Initial credit"
        )
        
        # Verify wallet is expired
        self.assertTrue(wallet.has_expired())
        
        # Try to consume value - should raise error
        with self.assertRaises(UserError) as context:
            wallet.consume_value(50.0)
        
        self.assertIn('expired', str(context.exception).lower())

    def test_refund_returns_units(self):
        """Test that refunding a POS order returns units to wallet"""
        # Create package and wallet
        package = self.env['bp.barber.package'].create({
            'name': 'Haircut x3',
            'code': 'HAIRCUT3',
            'package_type': 'qty',
        })
        
        self.env['bp.barber.package.line'].create({
            'package_id': package.id,
            'service_id': self.haircut_service.id,
            'qty': 3.0,
        })
        
        wallet = self.env['bp.barber.package.wallet'].create({
            'partner_id': self.partner.id,
            'package_id': package.id,
            'purchase_date': date.today(),
        })
        
        # Credit wallet
        wallet._create_wallet_line(
            move_type='credit',
            service_id=self.haircut_service.id,
            qty=3.0,
            note="Initial credit"
        )
        
        # Consume 1 unit
        wallet.consume_units(self.haircut_service, 1.0)
        self.assertEqual(wallet.get_available_units(self.haircut_service), 2.0)
        
        # Create redemption record
        redemption = self.env['bp.barber.package.redemption'].create({
            'wallet_id': wallet.id,
            'partner_id': self.partner.id,
            'origin_type': 'pos',
            'service_id': self.haircut_service.id,
            'qty': 1.0,
            'state': 'done',
        })
        
        # Reverse the redemption (simulate refund)
        redemption.action_reverse()
        
        # Verify units were returned
        wallet._compute_balances()  # Recompute
        self.assertEqual(wallet.get_available_units(self.haircut_service), 3.0)
        
        # Verify redemption is marked as reversed
        self.assertEqual(redemption.state, 'reversed')

    def test_package_without_customer_blocked(self):
        """Test that package sales without customer are blocked"""
        # Create package
        package = self.env['bp.barber.package'].create({
            'name': 'Test Package',
            'code': 'TEST',
            'package_type': 'value',
            'value_amount': 100.0,
        })
        
        # Create POS order WITHOUT partner
        pos_order = self.env['pos.order'].create({
            'name': 'Test Order',
            'partner_id': False,  # No customer
            'company_id': self.company.id,
            'date_order': datetime.now(),
        })
        
        pos_order_line = self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': package.pos_product_id.id,
            'qty': 1,
            'price_unit': 100.0,
            'price_subtotal_incl': 100.0,
        })
        
        # Attempt to create wallet - should raise error
        with self.assertRaises(UserError) as context:
            self.env['bp.barber.package.wallet'].credit_from_sale(
                self.env, pos_order_line
            )
        
        self.assertIn('customer', str(context.exception).lower())

    def test_bundle_package_multiple_services(self):
        """Test bundle package with multiple services"""
        # Create bundle package (2 Haircuts + 1 Shave)
        package = self.env['bp.barber.package'].create({
            'name': 'Grooming Bundle',
            'code': 'BUNDLE1',
            'package_type': 'bundle',
        })
        
        # Add multiple service lines
        self.env['bp.barber.package.line'].create({
            'package_id': package.id,
            'service_id': self.haircut_service.id,
            'qty': 2.0,
        })
        
        self.env['bp.barber.package.line'].create({
            'package_id': package.id,
            'service_id': self.shave_service.id,
            'qty': 1.0,
        })
        
        # Create wallet
        wallet = self.env['bp.barber.package.wallet'].create({
            'partner_id': self.partner.id,
            'package_id': package.id,
            'purchase_date': date.today(),
        })
        
        # Credit all services
        for line in package.line_ids:
            wallet._create_wallet_line(
                move_type='credit',
                service_id=line.service_id.id,
                qty=line.qty,
                note="Bundle credit"
            )
        
        # Verify both services have correct units
        self.assertEqual(wallet.get_available_units(self.haircut_service), 2.0)
        self.assertEqual(wallet.get_available_units(self.shave_service), 1.0)
        
        # Consume 1 haircut
        wallet.consume_units(self.haircut_service, 1.0)
        
        # Verify balances
        self.assertEqual(wallet.get_available_units(self.haircut_service), 1.0)
        self.assertEqual(wallet.get_available_units(self.shave_service), 1.0)