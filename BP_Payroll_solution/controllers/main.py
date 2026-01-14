import csv
import io
from odoo import http
from odoo.http import request, content_disposition

class PayrollCSVReport(http.Controller):

    @http.route('/print/payslip/csv/<model("hr.payslip"):payslip>', type='http', auth='user')
    def download_payslip_csv(self, payslip, **kw):
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Header Information
        writer.writerow(['Company', payslip.company_id.name])
        address = payslip.company_id.partner_id.contact_address if payslip.company_id.partner_id else ''
        address = address.replace('\n', ' ').replace('\r', '') if address else ''
        writer.writerow(['Address', address])
        writer.writerow([])
        
        # Employee Information
        writer.writerow(['Employee Name', payslip.employee_id.name])
        writer.writerow(['Employee ID', payslip.employee_id.identification_id or ''])
        writer.writerow(['Department', payslip.employee_id.department_id.name or ''])
        writer.writerow(['Job Title', payslip.employee_id.job_id.name or ''])
        writer.writerow(['Pay Period', f"{payslip.date_from} to {payslip.date_to}"])
        writer.writerow([])

        # Earnings Section
        writer.writerow(['EARNINGS'])
        writer.writerow(['Name', 'Code', 'Amount'])
        earnings = payslip.line_ids.filtered(lambda l: l.category_id.code == 'EARN')
        for line in earnings:
            writer.writerow([line.name, line.code, line.total])
        writer.writerow(['Total Earnings', '', payslip.total_earnings])
        writer.writerow([])

        # Deductions Section
        writer.writerow(['DEDUCTIONS'])
        writer.writerow(['Name', 'Code', 'Amount'])
        deductions = payslip.line_ids.filtered(lambda l: l.category_id.code == 'DED')
        for line in deductions:
            writer.writerow([line.name, line.code, abs(line.total)])
        writer.writerow(['Total Deductions', '', payslip.total_deductions])
        writer.writerow([])

        # Net Pay
        writer.writerow(['NET PAY', '', payslip.total_net_pay])

        # Prepare Response
        filename = f"Payslip_{payslip.employee_id.name}_{payslip.date_to}.csv"
        response = request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'text/csv'),
                ('Content-Disposition', content_disposition(filename)),
            ]
        )
        return response
