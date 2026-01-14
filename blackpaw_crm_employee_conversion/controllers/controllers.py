# -*- coding: utf-8 -*-
# from odoo import http


# class CrmEmployeeConversion(http.Controller):
#     @http.route('/crm_employee_conversion/crm_employee_conversion', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/crm_employee_conversion/crm_employee_conversion/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('crm_employee_conversion.listing', {
#             'root': '/crm_employee_conversion/crm_employee_conversion',
#             'objects': http.request.env['crm_employee_conversion.crm_employee_conversion'].search([]),
#         })

#     @http.route('/crm_employee_conversion/crm_employee_conversion/objects/<model("crm_employee_conversion.crm_employee_conversion"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('crm_employee_conversion.object', {
#             'object': obj
#         })

