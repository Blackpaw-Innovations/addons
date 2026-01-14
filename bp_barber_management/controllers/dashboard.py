# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class BarberDashboardController(http.Controller):
    """Controller for barber dashboard KPI endpoints"""

    @http.route('/bp_barber/kpi', type='json', auth='user', methods=['POST'])
    def get_kpis(self, **kwargs):
        """
        Get KPI data for dashboard
        
        Expected JSON payload:
        {
            "period": "today" | "7d" | "30d" | "custom",
            "date_from": "YYYY-MM-DD" (required if period=custom),
            "date_to": "YYYY-MM-DD" (required if period=custom),
            "company_id": int (optional, defaults to current user's company)
        }
        
        Returns:
        {
            "period": "...",
            "from": "YYYY-MM-DD", 
            "to": "YYYY-MM-DD",
            "tiles": {
                "revenue_by_barber": [...],
                "revenue_by_service": [...], 
                "utilization": {...},
                "no_show_rate": {...},
                "attach_rate": {...},
                "top_consumables": [...]
            }
        }
        """
        try:
            # Get request payload
            payload = request.jsonrequest or {}
            
            # Validate period
            period = payload.get('period', '7d')
            if period not in ['today', '7d', '30d', 'custom']:
                period = '7d'
            
            # Validate custom dates
            if period == 'custom':
                date_from = payload.get('date_from')
                date_to = payload.get('date_to')
                if not date_from or not date_to:
                    return {
                        'error': 'date_from and date_to are required when period=custom',
                        'code': 'MISSING_DATES'
                    }
            
            # Get company
            company_id = payload.get('company_id')
            if not company_id:
                company_id = request.env.user.company_id.id
            
            # Validate company access
            company = request.env['res.company'].sudo().browse(company_id)
            if not company.exists():
                return {
                    'error': 'Invalid company_id',
                    'code': 'INVALID_COMPANY'
                }
            
            # Get KPI service and compute all metrics
            kpi_service = request.env['bp.barber.kpi.service']
            result = kpi_service.get_all_kpis(payload)
            
            return result
            
        except Exception as e:
            _logger.error(f"Error in KPI endpoint: {e}")
            return {
                'error': f'Internal server error: {str(e)}',
                'code': 'SERVER_ERROR'
            }

    @http.route('/bp_barber/kpi', type='http', auth='user', methods=['GET'])
    def get_kpis_http(self, **kwargs):
        """
        HTTP GET version of KPI endpoint for testing
        
        Query parameters:
        - period: today|7d|30d|custom
        - date_from: YYYY-MM-DD (if custom)
        - date_to: YYYY-MM-DD (if custom) 
        - company_id: int (optional)
        """
        try:
            # Convert GET params to JSON payload format
            payload = {
                'period': kwargs.get('period', '7d'),
                'date_from': kwargs.get('date_from'),
                'date_to': kwargs.get('date_to'),
                'company_id': int(kwargs.get('company_id', 0)) or None
            }
            
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            # Use same logic as JSON endpoint
            if payload.get('period') not in ['today', '7d', '30d', 'custom']:
                payload['period'] = '7d'
                
            if payload.get('period') == 'custom':
                if not payload.get('date_from') or not payload.get('date_to'):
                    return request.make_response(
                        json.dumps({
                            'error': 'date_from and date_to are required when period=custom',
                            'code': 'MISSING_DATES'
                        }),
                        headers={'Content-Type': 'application/json'}
                    )
            
            if not payload.get('company_id'):
                payload['company_id'] = request.env.user.company_id.id
                
            # Get KPI service and compute
            kpi_service = request.env['bp.barber.kpi.service']
            result = kpi_service.get_all_kpis(payload)
            
            return request.make_response(
                json.dumps(result, indent=2, default=str),
                headers={'Content-Type': 'application/json'}
            )
            
        except Exception as e:
            _logger.error(f"Error in HTTP KPI endpoint: {e}")
            return request.make_response(
                json.dumps({
                    'error': f'Internal server error: {str(e)}',
                    'code': 'SERVER_ERROR'
                }),
                headers={'Content-Type': 'application/json'}
            )

    @http.route('/bp_barber/dashboard/test', type='http', auth='user')
    def test_dashboard(self, **kwargs):
        """Test endpoint to verify controller is working"""
        return f"""
        <html>
            <head><title>Barber Dashboard Test</title></head>
            <body>
                <h1>Barber Dashboard Controller Test</h1>
                <p>Controller is working! Current user: {request.env.user.name}</p>
                <p>Company: {request.env.user.company_id.name}</p>
                <p><a href="/bp_barber/kpi?period=7d">Test KPI Endpoint (7 days)</a></p>
                <p><a href="/bp_barber/kpi?period=today">Test KPI Endpoint (Today)</a></p>
            </body>
        </html>
        """