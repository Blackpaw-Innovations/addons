# Payroll Module UI Testing Instructions

This document outlines the step-by-step testing procedures for the **BP_Payroll_solution** module in Odoo 17 Community. It focuses on the User Interface (UI) workflows to ensure the module functions correctly from an end-user perspective.

## Prerequisites

1.  **User Access**: Ensure you are logged in as a user with **Payroll Manager** access rights.
2.  **Module Installation**: The `BP_Payroll_solution` module must be installed.
3.  **Company Settings**: Ensure the company has a default payroll journal and currency configured.

---

## Role-Based Workflow Breakdown

### 👤 HR Officer / Payroll Manager
**Responsibilities**: Employee Data, Contracts, Payroll Computation.

1.  **Employee Onboarding**:
    *   Create Employee records.
    *   Define **Contracts** with the correct **Salary Structure** and **Wage**.
2.  **Payroll Processing**:
    *   Create **Payslip Batches** (Pay Runs) for the period.
    *   **Compute** sheets to calculate Gross, Net, and Deductions.
    *   Verify statutory deductions (PAYE, NSSF, SHIF) on individual slips.
3.  **Reporting**:
    *   Generate Payslip Lines reports for internal analysis.

### 📊 Accountant
**Responsibilities**: Financial Posting, Reconciliation, Payment.

1.  **Configuration Verification**:
    *   Ensure the **Payroll Journal** is configured.
    *   Verify **Salary Rules** are mapped to the correct Debit/Credit accounts.
2.  **Journal Entry Validation**:
    *   After the Payroll Manager closes a batch, check the generated **Journal Entry**.
    *   Verify that **Debits** (Expenses) match **Credits** (Liabilities/Payables).
3.  **Payment**:
    *   Register payment for the Net Salary to employees.
    *   Remit statutory deductions to authorities.

---

## Test Case 1: Configuration & Statutory Setup

**Objective**: Verify that statutory tables (Tax Bands, Contributions) can be configured.

1.  **Navigate to Statutory Tables**:
    *   Go to **Payroll** > **Configuration** > **Salary** > **Statutory Tables**.
    *   Click on **Tax Bands**.
2.  **Create Tax Band**:
    *   Click **New**.
    *   Enter a name (e.g., "2024 Tax Band").
    *   Add lines for tax brackets (e.g., 0-1000 @ 0%, 1001-5000 @ 10%, etc.).
    *   Save the record.
3.  **Create Contribution**:
    *   Go to **Payroll** > **Configuration** > **Salary** > **Statutory Tables** > **Contributions**.
    *   Click **New**.
    *   Enter a name (e.g., "National Pension").
    *   Set the Employee Rate (%) and Employer Rate (%).
    *   Save.

**Expected Result**: Records are saved successfully without errors.

---

## Test Case 1.1: Chart of Accounts Mapping

**Objective**: Ensure Salary Rules are correctly mapped to the Chart of Accounts for automatic journal entry creation.

1.  **Navigate to Salary Rules**:
    *   Go to **Payroll** > **Configuration** > **Salary** > **Rules**.wha
2.  **Select a Rule**:
    *   Open a rule that requires accounting entries (e.g., **Basic Salary**, **Net Salary**, **PAYE**).
3.  **Configure Accounting Tab**:
    *   Click the **Accounting** tab on the rule form.
    *   **Debit Account**: Select the expense account (e.g., "Salaries Expense" for Basic Salary).
    *   **Credit Account**: Select the liability account (e.g., "Salaries Payable" for Net Salary, or "PAYE Payable" for tax rules).
    *   *Note*: Typically, earning rules debit an expense account, while deduction rules credit a liability account.
4.  **Save**:
    *   Save the rule configuration.

**Expected Result**: When a payslip is confirmed, the journal entry will use these mapped accounts.

---

## Test Case 2: Employee & Contract Management

**Objective**: Ensure an employee has a valid contract and salary structure.

1.  **Create Employee**:
    *   Go to **Payroll** > **Employees** > **Employees**.
    *   Click **New**.
    *   Enter **Name** (e.g., "John Doe").
    *   Save.
2.  **Create Contract**:
    *   On the Employee form, click the **Contracts** smart button (or go to **Employees** app > Contracts).
    *   Click **New**.
    *   Set **Contract Reference** (e.g., "JD-2024").
    *   Select the **Employee** created above.
    *   Set **Start Date**.
    *   **Important**: Under the **Salary Information** tab (or similar), ensure a **Salary Structure Type** and **Salary Structure** are selected.
    *   Set a **Wage** (e.g., 5000).
    *   Change state to **Running**.
    *   Save.

**Expected Result**: Employee has a running contract with a defined salary structure.

---

## Test Case 3: Payroll Processing (Batch Workflow)

**Objective**: Test the end-to-end payroll processing for a group of employees.

1.  **Create Payslip Batch**:
    *   Go to **Payroll** > **Payslips** > **Pay Runs**.
    *   Click **New**.
    *   Enter **Name** (e.g., "January 2024 Payroll").
    *   Select the **Period** (Start Date and End Date).
    *   Save the batch.
2.  **Add Payslips**:
    *   In the **Payslips** tab, click **Add a line**.
    *   Select the employees to include in this batch.
    *   *Note*: Ensure the employees have valid contracts for the selected period.
3.  **Compute**:
    *   Click the **Compute** button in the header.
    *   *Verify*: The **Total Net** and other computed totals in the "Totals (computed)" group are updated.
4.  **Verify Calculations**:
    *   Open one of the payslips from the list.
    *   Check the **Lines** tab (or Salary Computation).
    *   Verify that **Basic Salary**, **Gross**, **Deductions**, and **Net Salary** are calculated correctly.
5.  **Process & Close**:
    *   Go back to the Batch.
    *   Click **Pre-Validate** (if required).
    *   Click **Mark Slips Ready for Payment**.
    *   Click **Close** to finalize the batch.
    *   Verify that the state changes to **Done**.

**Expected Result**: Batch is processed, payslips are calculated, and the batch is closed successfully.

---

## Test Case 4: Individual Payslip Creation

**Objective**: Manually create a single payslip for an employee.

1.  **Create Payslip**:
    *   Go to **Payroll** > **Payslips** > **Payslips**.
    *   Click **New**.
    *   Select **Employee**.
    *   The **Contract** and **Structure** should auto-populate.
    *   Select the **Period**.
2.  **Compute**:
    *   Click the **Compute** button.
    *   Check the **Lines** tab for salary components.
    *   Check the **Totals** tab for Gross, Deduction, and Net values.
3.  **Process**:
    *   Click **Verify** to move to the verification stage.
    *   Click **Mark Ready for Payment**.
    *   Click **Mark Done** to finalize the payslip.
    *   Verify the state changes to **Done**.

**Expected Result**: Payslip is created, computed, and processed to Done state successfully.

---

## Test Case 5: Reporting

**Objective**: Verify that payroll reports can be generated.

1.  **Payslip Lines Report**:
    *   Go to **Payroll** > **Reporting** > **Payslip Lines**.
    *   Use the Pivot view to analyze salary components by Department or Employee.
2.  **Work Entries Analysis**:
    *   Go to **Payroll** > **Reporting** > **Work Entries Analysis**.
    *   Check attendance/leave data impact on payroll.

**Expected Result**: Reports load with data corresponding to the processed payslips.

---

## Troubleshooting

*   **No Rules Found**: If the payslip computes to zero, check that the Contract has a Salary Structure, and the Structure has active Salary Rules.
*   **Missing Journal**: If you cannot confirm the payslip, ensure a Payroll Journal is set in the Company Settings or Structure.
