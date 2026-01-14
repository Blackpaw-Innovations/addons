# BP POS Invoice Payment Bridge - Testing Instructions

This document outlines the steps to verify the functionality of the `bp_pos_pay_invoice` module, which allows paying customer invoices directly from the Point of Sale.

## 1. Configuration

1.  Navigate to **Point of Sale > Configuration > Settings**.
2.  Scroll down to the **Enable Optical Features** section.
3.  Ensure **Enable Optical Features** is checked.
4.  Enable **Allow Invoice Payments**.
5.  (Optional) Enable **Allow Partial Payments** to test partial payments.
6.  Click **Save**.

## 2. Pre-requisites

1.  Go to **Invoicing > Customers > Invoices**.
2.  Create a new invoice for a test customer (e.g., "Azure Interior").
3.  Add invoice lines and **Confirm** the invoice.
    *   *Note the Total Amount Due (e.g., $100).*
4.  Ensure your POS shop has at least one valid payment method configured (e.g., Cash or Bank).

## 3. Execution (POS Session)

1.  Open a new **POS Session** (or resume an existing one).
2.  **Select the Customer** for whom you created the invoice (e.g., "Azure Interior").
3.  Click the **"Pay Invoice"** button (located in the control buttons area).
4.  A popup will appear listing all open invoices for this customer.
5.  **Select the invoice** you created in step 2.
6.  Enter the **Payment Amount**:
    *   *Test Case A (Full Payment):* Leave the default full amount.
    *   *Test Case B (Partial Payment):* Enter a partial amount (e.g., $50) if enabled.
7.  Click **Confirm**.
    *   *Observation:* A new line is added to the order cart representing the invoice payment.
8.  Click **Payment** and process the transaction using a payment method (e.g., Cash).
9.  **Validate** the order.

## 4. Verification

### A. Check POS Order
1.  Go to **Point of Sale > Orders > Orders**.
2.  Open the order you just created.
3.  Verify the checkbox **Is Invoice Payment** is checked.
4.  Verify the **Invoice** field links to the correct invoice.

### B. Check Invoice Status
1.  Go to **Invoicing > Customers > Invoices**.
2.  Open the original invoice.
3.  **Status Check:**
    *   If you paid in full: The status should be **Paid**.
    *   If you paid partially: The status should be **Partial**, and the *Amount Due* should be reduced by the paid amount.

### C. Check Accounting Entries
1.  On the invoice form, scroll to the bottom.
2.  You should see a payment widget indicating the payment linked to this invoice.
3.  Click the information icon (i) on the payment line to view the payment details.
4.  Verify the **Payment Reference** or **Memo** mentions "POS [Order Ref] - Invoice Payment".
