# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OpticalPatientInsurance(models.Model):
    _name = "optical.patient.insurance"
    _description = "Patient Insurance"
    _order = "date desc, id desc"

    name = fields.Char(string="Policy Number", required=True)
    patient_id = fields.Many2one(
        comodel_name="res.partner",
        string="Patient",
        required=True,
        ondelete="cascade"
    )
    insurance_company_id = fields.Many2one(
        comodel_name="optical.insurance.company",
        string="Insurance Company",
        required=True
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.today)
    expiry_date = fields.Date(string="Expiry Date")
    patient_company_id = fields.Char(string="Patient Company")
    invoice_number = fields.Char(string="Invoice Number")
    document_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="optical_insurance_attachment_rel",
        column1="insurance_id",
        column2="attachment_id",
        string="Documents"
    )
    coverage_details = fields.Text(string="Coverage Details")
    active = fields.Boolean(string="Active", default=True)
    note = fields.Text(string="Note")
