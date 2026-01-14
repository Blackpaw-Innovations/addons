from odoo.tests.common import TransactionCase, tagged
from datetime import date


@tagged("post_install", "-at_install")
class TestKenyaPayroll(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Company = self.env["res.company"]
        self.Employee = self.env["hr.employee"]
        self.Contract = self.env["hr.contract"]
        self.Payslip = self.env["hr.payslip"]
        self.PayrollConfig = self.env["bp.payroll.ke.config"]
        self.Structure = self.env["hr.payroll.structure"]

    def test_ke_payslip_basic(self):
        kenya = self.env.ref("base.ke")
        company = self.Company.create({"name": "KE Co", "country_id": kenya.id})
        config = self.PayrollConfig.create({"company_id": company.id})
        structure = self.Structure.search([("code", "=", "KE_BASIC_STRUCTURE")], limit=1)
        self.assertTrue(structure, "Kenya structure must exist")

        employee = self.Employee.create({"name": "Test Emp", "company_id": company.id})
        contract = self.Contract.create(
            {
                "name": "Test Contract",
                "employee_id": employee.id,
                "company_id": company.id,
                "wage": 100000.0,
                "date_start": date(2025, 1, 1),
                "payroll_country_code": "KE",
                "structure_id": structure.id,
            }
        )

        slip = self.Payslip.create(
            {
                "name": "Jan 2025",
                "employee_id": employee.id,
                "company_id": company.id,
                "contract_id": contract.id,
                "date_from": date(2025, 1, 1),
                "date_to": date(2025, 1, 31),
                "structure_id": structure.id,
                "payroll_country_code": "KE",
            }
        )
        slip.action_compute_inputs()
        lines = {line.code: line.total for line in slip.line_ids}
        self.assertGreater(lines.get("NSSF_EMP", 0), 0)
        self.assertGreaterEqual(lines.get("SHIF", 0), config.shif_min_contribution)
        self.assertGreater(lines.get("PAYE", 0), 0)
        self.assertTrue(lines.get("NET", 0) < lines.get("GROSS", 0))
        self.assertAlmostEqual(
            lines.get("NET", 0),
            lines.get("GROSS", 0) - (lines.get("NSSF_EMP", 0) + lines.get("SHIF", 0) + lines.get("PAYE", 0)),
            places=2,
        )
