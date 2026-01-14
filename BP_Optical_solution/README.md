# BP POS Invoice Payment Bridge

Pay customer invoices (deposits and balances) directly from Odoo Point of Sale and reconcile them in accounting.

## Features

- **Pay Invoices from POS**: Allow POS users to select and pay open customer invoices directly from the POS interface
- **Full & Partial Payments**: Support for both full invoice payments and partial payments (configurable)
- **Automatic Reconciliation**: Payments are automatically reconciled with the corresponding invoice in accounting
- **Smart Button Visibility**: "Pay Invoice" button only appears when the selected customer has open invoices
- **Invoice Selection Popup**: User-friendly popup to browse and select from customer's open invoices

## Requirements

- Odoo 17.0
- `point_of_sale` module
- `account` module
- `BP_Optical_solution` module (dependency)

## Installation

1. Copy the `BP_Optical_solution` folder to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the module from Apps menu

## Configuration

1. Navigate to **Point of Sale > Configuration > Settings**
2. Scroll down to the **Enable Optical Features** section
3. Enable **Allow Invoice Payments**
4. (Optional) Enable **Allow Partial Payments** to allow partial invoice payments
5. Click **Save**

## Usage

1. Open a POS session
2. Select a customer who has open invoices
3. Click the **"Pay Invoice"** button (appears only if customer has open invoices)
4. Select an invoice from the popup
5. Enter the payment amount (or leave default for full payment)
6. Click **Confirm** to add the payment to the order
7. Complete the POS order as usual

## Module Structure

```
BP_Optical_solution/
├── __init__.py
├── __manifest__.py
├── README.md
├── TESTING_INSTRUCTIONS.md
├── data/
│   └── product_data.xml          # Invoice payment product
├── models/
│   ├── __init__.py
│   ├── account_move.py           # Invoice extensions
│   ├── pos_config.py             # POS config settings
│   └── pos_order.py              # POS order extensions & payment processing
├── security/
│   └── ir.model.access.csv       # Access rights
├── static/src/
│   ├── js/
│   │   ├── InvoicePaymentButton.js    # POS control button
│   │   ├── InvoicePaymentPopup.js     # Invoice selection popup
│   │   └── pos_order_invoice_payment.js
│   └── xml/
│       ├── InvoicePaymentPopup.xml    # OWL templates
│       └── InvoicePaymentReceipt.xml
├── views/
│   ├── account_move_views.xml
│   ├── pos_config_views.xml
│   └── pos_order_views.xml
└── wizards/
    ├── __init__.py
    └── pos_invoice_payment_wizard.py  # Invoice fetching wizard
```

## Technical Details

### POS Order Fields

- `is_invoice_payment`: Boolean flag indicating if the order is an invoice payment
- `invoice_id`: Many2one link to the paid invoice
- `invoice_payment_amount`: Amount paid towards the invoice
- `invoice_payment_mode`: Payment mode ('full' or 'partial')

### Payment Processing

When a POS order with invoice payment is validated:
1. A payment is created and linked to the invoice
2. The payment is automatically reconciled with the invoice
3. Invoice status updates to 'Paid' (full) or 'Partial' (partial payment)

## License

LGPL-3

## Author

**Blackpaw Innovations**  
Developer: Papa Driss  
Website: https://www.blackpawinnovations.com/

## Support

For issues or feature requests, please contact Blackpaw Innovations.
