# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestConsumables(TransactionCase):

    def setUp(self):
        super().setUp()
        
        # Create test company and currency
        self.company = self.env.company
        self.currency = self.company.currency_id
        
        # Create test consumable products
        self.razor_blade = self.env['product.product'].create({
            'name': 'Razor Blade',
            'type': 'consu',
            'list_price': 2.50,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        
        self.aftershave = self.env['product.product'].create({
            'name': 'Aftershave',
            'type': 'consu', 
            'list_price': 15.00,
            'uom_id': self.env.ref('uom.product_uom_litre').id,
        })
        
        # Create test service with BOM
        self.haircut_service = self.env['bp.barber.service'].create({
            'name': 'Premium Haircut',
            'duration_minutes': 45,
            'list_price': 75.00,
        })
        
        # Create test barber
        self.barber = self.env['bp.barber.barber'].create({
            'name': 'Master Barber',
            'barber_code': 'MB01',
            'email': 'master@barber.com',
        })

    def test_usage_created_on_appointment_finish(self):
        """Test that usage records are created when appointment is finished"""
        # Create BOM for haircut service
        self.env['bp.barber.service.bom'].create({
            'service_id': self.haircut_service.id,
            'product_id': self.razor_blade.id,
            'qty': 1.0,
            'uom_id': self.razor_blade.uom_id.id,
        })
        
        self.env['bp.barber.service.bom'].create({
            'service_id': self.haircut_service.id,
            'product_id': self.aftershave.id,
            'qty': 0.05,  # 50ml
            'uom_id': self.aftershave.uom_id.id,
        })
        
        # Create appointment
        appointment = self.env['bp.barber.appointment'].create({
            'name': 'Test Appointment',
            'barber_id': self.barber.id,
            'start_datetime': datetime.now(),
            'service_ids': [(6, 0, [self.haircut_service.id])],
            'state': 'in_service',
        })
        
        # Finish appointment
        appointment.action_finish_service()
        
        # Check usage record was created
        usage_records = self.env['bp.barber.consumable.usage'].search([
            ('barber_id', '=', self.barber.id),
            ('appointment_id', '=', appointment.id)
        ])
        
        self.assertEqual(len(usage_records), 1, "Usage record should be created")
        
        usage = usage_records[0]
        self.assertEqual(usage.origin_type, 'appointment')
        self.assertEqual(len(usage.line_ids), 2, "Should have 2 usage lines")
        
        # Check usage quantities
        razor_line = usage.line_ids.filtered(lambda l: l.product_id == self.razor_blade)
        aftershave_line = usage.line_ids.filtered(lambda l: l.product_id == self.aftershave)
        
        self.assertEqual(razor_line.qty, 1.0)
        self.assertEqual(aftershave_line.qty, 0.05)

    def test_usage_created_on_pos_payment_per_barber(self):
        """Test that usage records are created per barber when POS order is paid"""
        # Create another barber
        barber2 = self.env['bp.barber.barber'].create({
            'name': 'Junior Barber',
            'barber_code': 'JB01', 
            'email': 'junior@barber.com',
        })
        
        # Create BOM
        self.env['bp.barber.service.bom'].create({
            'service_id': self.haircut_service.id,
            'product_id': self.razor_blade.id,
            'qty': 1.0,
            'uom_id': self.razor_blade.uom_id.id,
        })
        
        # Create service product for POS
        service_product = self.env['product.product'].create({
            'name': 'Haircut Service Product',
            'type': 'service',
            'list_price': 75.00,
        })
        
        # Link service to product
        self.haircut_service.product_id = service_product.id
        
        # Create POS order with lines assigned to different barbers
        pos_order = self.env['pos.order'].create({
            'name': 'POS/001',
            'company_id': self.company.id,
            'date_order': datetime.now(),
        })
        
        # Line 1: assigned to barber 1
        line1 = self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': service_product.id,
            'barber_id': self.barber.id,
            'qty': 2,  # 2 haircuts
            'price_unit': 75.00,
        })
        
        # Line 2: assigned to barber 2  
        line2 = self.env['pos.order.line'].create({
            'order_id': pos_order.id,
            'product_id': service_product.id,
            'barber_id': barber2.id,
            'qty': 1,  # 1 haircut
            'price_unit': 75.00,
        })
        
        # Process consumable usage (simulate payment)
        pos_order._create_consumable_usage(pos_order)
        
        # Check usage records were created for each barber
        usage1 = self.env['bp.barber.consumable.usage'].search([
            ('barber_id', '=', self.barber.id),
            ('pos_order_id', '=', pos_order.id)
        ])
        
        usage2 = self.env['bp.barber.consumable.usage'].search([
            ('barber_id', '=', barber2.id),
            ('pos_order_id', '=', pos_order.id)
        ])
        
        self.assertEqual(len(usage1), 1, "Usage record for barber 1 should be created")
        self.assertEqual(len(usage2), 1, "Usage record for barber 2 should be created")
        
        # Check quantities (2 services for barber 1, 1 for barber 2)
        self.assertEqual(usage1.line_ids[0].qty, 2.0, "Barber 1 should have 2 razor blades used")
        self.assertEqual(usage2.line_ids[0].qty, 1.0, "Barber 2 should have 1 razor blade used")

    def test_ledger_balances_without_stock(self):
        """Test ledger balance calculations when stock module is not available"""
        # Mock stock module as not installed
        with patch.object(self.env.registry, '_init_modules', {}):
            # Issue products to barber via wizard
            wizard = self.env['bp.barber.consumable.issue.wizard'].create({
                'barber_id': self.barber.id,
                'note': 'Initial issue',
                'line_ids': [(0, 0, {
                    'product_id': self.razor_blade.id,
                    'qty': 10.0,
                    'uom_id': self.razor_blade.uom_id.id,
                })]
            })
            
            wizard.action_issue()
            
            # Check ledger entries were created
            ledger_entries = self.env['bp.barber.consumable.ledger'].search([
                ('barber_id', '=', self.barber.id),
                ('product_id', '=', self.razor_blade.id)
            ])
            
            self.assertEqual(len(ledger_entries), 1, "Ledger entry should be created")
            self.assertEqual(ledger_entries[0].move_type, 'issue')
            self.assertEqual(ledger_entries[0].qty, 10.0)
            
            # Check balance calculation
            balance = self.env['bp.barber.consumable.ledger'].get_balance(
                self.barber.id, self.razor_blade.id
            )
            self.assertEqual(balance, 10.0, "Balance should be 10 after issue")
            
            # Create consumption
            self.env['bp.barber.consumable.ledger'].create({
                'barber_id': self.barber.id,
                'product_id': self.razor_blade.id,
                'move_type': 'consume',
                'qty': 3.0,
                'uom_id': self.razor_blade.uom_id.id,
                'origin_note': 'Test consumption'
            })
            
            # Check updated balance
            new_balance = self.env['bp.barber.consumable.ledger'].get_balance(
                self.barber.id, self.razor_blade.id
            )
            self.assertEqual(new_balance, 7.0, "Balance should be 7 after consumption")

    def test_replenishment_suggests_to_target(self):
        """Test replenishment suggestion generation"""
        # Create supply profile
        supply_profile = self.env['bp.barber.barber.supply'].create({
            'barber_id': self.barber.id,
            'product_id': self.razor_blade.id,
            'min_qty': 2.0,
            'target_qty': 10.0,
        })
        
        # Create some historical usage (for avg daily usage calculation)
        usage = self.env['bp.barber.consumable.usage'].create({
            'name': 'Historical Usage',
            'barber_id': self.barber.id,
            'origin_type': 'appointment',
            'date': datetime.now() - timedelta(days=15),
            'line_ids': [(0, 0, {
                'product_id': self.razor_blade.id,
                'qty': 5.0,
                'uom_id': self.razor_blade.uom_id.id,
            })]
        })
        
        # Mock current balance
        with patch.object(supply_profile, 'get_current_balance', return_value=3.0):
            # Generate suggestions
            suggestions_data = self.env['bp.barber.consumable.suggestion'].generate_suggestions(
                self.env, [self.barber.id]
            )
            
            self.assertEqual(len(suggestions_data), 1, "Should generate 1 suggestion")
            
            suggestion_data = suggestions_data[0]
            self.assertEqual(suggestion_data['barber_id'], self.barber.id)
            self.assertEqual(suggestion_data['product_id'], self.razor_blade.id)
            self.assertEqual(suggestion_data['on_hand'], 3.0)
            self.assertEqual(suggestion_data['min_qty'], 2.0)
            self.assertEqual(suggestion_data['target_qty'], 10.0)
            self.assertEqual(suggestion_data['suggest_qty'], 7.0)  # 10 - 3 = 7

    def test_stock_move_if_stock_installed(self):
        """Test stock move creation when stock module is installed"""
        # Mock stock module as installed
        stock_modules = {'stock': True}
        
        with patch.object(self.env.registry, '_init_modules', stock_modules):
            # Mock stock location for barber
            mock_location = MagicMock()
            mock_location.id = 100
            
            with patch.object(self.barber, 'stock_location_id', mock_location):
                with patch.object(self.barber, '_get_or_create_stock_location', return_value=mock_location):
                    # Mock consumption location
                    mock_consumption_location = MagicMock()
                    mock_consumption_location.id = 200
                    
                    # Create usage record
                    usage = self.env['bp.barber.consumable.usage'].create({
                        'name': 'Test Usage',
                        'barber_id': self.barber.id,
                        'origin_type': 'appointment',
                        'state': 'draft',
                        'line_ids': [(0, 0, {
                            'product_id': self.razor_blade.id,
                            'qty': 2.0,
                            'uom_id': self.razor_blade.uom_id.id,
                        })]
                    })
                    
                    # Mock stock move creation
                    with patch.object(usage, '_get_consumption_location', return_value=mock_consumption_location):
                        with patch('odoo.addons.stock.models.stock_move.StockMove') as mock_stock_move:
                            mock_move_instance = MagicMock()
                            mock_stock_move.create.return_value = mock_move_instance
                            
                            # Process consumption
                            usage._create_stock_moves()
                            
                            # Verify stock move was created
                            mock_stock_move.create.assert_called_once()
                            call_args = mock_stock_move.create.call_args[0][0]
                            
                            self.assertEqual(call_args['product_id'], self.razor_blade.id)
                            self.assertEqual(call_args['product_uom_qty'], 2.0)
                            self.assertEqual(call_args['location_id'], mock_location.id)
                            self.assertEqual(call_args['location_dest_id'], mock_consumption_location.id)

    def test_bom_constraints_and_validations(self):
        """Test BOM model constraints and validations"""
        # Test unique constraint
        self.env['bp.barber.service.bom'].create({
            'service_id': self.haircut_service.id,
            'product_id': self.razor_blade.id,
            'qty': 1.0,
            'uom_id': self.razor_blade.uom_id.id,
        })
        
        # Try to create duplicate - should fail
        with self.assertRaises(Exception):  # Should raise IntegrityError
            self.env['bp.barber.service.bom'].create({
                'service_id': self.haircut_service.id,
                'product_id': self.razor_blade.id,
                'qty': 2.0,
                'uom_id': self.razor_blade.uom_id.id,
            })
        
        # Test positive quantity constraint
        with self.assertRaises(ValidationError):
            self.env['bp.barber.service.bom'].create({
                'service_id': self.haircut_service.id,
                'product_id': self.aftershave.id,
                'qty': -1.0,  # Negative quantity
                'uom_id': self.aftershave.uom_id.id,
            })

    def test_supply_profile_constraints(self):
        """Test supply profile model constraints"""
        # Test negative quantities
        with self.assertRaises(ValidationError):
            self.env['bp.barber.barber.supply'].create({
                'barber_id': self.barber.id,
                'product_id': self.razor_blade.id,
                'min_qty': -1.0,  # Negative min
                'target_qty': 10.0,
            })
        
        # Test min > target
        with self.assertRaises(ValidationError):
            self.env['bp.barber.barber.supply'].create({
                'barber_id': self.barber.id,
                'product_id': self.razor_blade.id,
                'min_qty': 15.0,  # Min greater than target
                'target_qty': 10.0,
            })
        
        # Test unique constraint
        self.env['bp.barber.barber.supply'].create({
            'barber_id': self.barber.id,
            'product_id': self.razor_blade.id,
            'min_qty': 2.0,
            'target_qty': 10.0,
        })
        
        # Try to create duplicate - should fail
        with self.assertRaises(Exception):  # Should raise IntegrityError
            self.env['bp.barber.barber.supply'].create({
                'barber_id': self.barber.id,
                'product_id': self.razor_blade.id,
                'min_qty': 3.0,
                'target_qty': 12.0,
            })

    def test_usage_aggregation_from_multiple_services(self):
        """Test that multiple services with same products aggregate correctly"""
        # Create another service with same razor blade
        shave_service = self.env['bp.barber.service'].create({
            'name': 'Traditional Shave',
            'duration_minutes': 30,
            'list_price': 50.00,
        })
        
        # Create BOM for both services using same product
        self.env['bp.barber.service.bom'].create({
            'service_id': self.haircut_service.id,
            'product_id': self.razor_blade.id,
            'qty': 1.0,
            'uom_id': self.razor_blade.uom_id.id,
        })
        
        self.env['bp.barber.service.bom'].create({
            'service_id': shave_service.id,
            'product_id': self.razor_blade.id,
            'qty': 2.0,  # Shave uses 2 blades
            'uom_id': self.razor_blade.uom_id.id,
        })
        
        # Create appointment with both services
        appointment = self.env['bp.barber.appointment'].create({
            'name': 'Haircut + Shave',
            'barber_id': self.barber.id,
            'start_datetime': datetime.now(),
            'service_ids': [(6, 0, [self.haircut_service.id, shave_service.id])],
            'state': 'in_service',
        })
        
        # Finish appointment
        appointment.action_finish_service()
        
        # Check usage aggregation
        usage = self.env['bp.barber.consumable.usage'].search([
            ('barber_id', '=', self.barber.id),
            ('appointment_id', '=', appointment.id)
        ])
        
        self.assertEqual(len(usage), 1, "Should create single usage record")
        self.assertEqual(len(usage.line_ids), 1, "Should have 1 aggregated line")
        
        razor_line = usage.line_ids.filtered(lambda l: l.product_id == self.razor_blade)
        self.assertEqual(razor_line.qty, 3.0, "Should aggregate 1 + 2 = 3 razor blades")