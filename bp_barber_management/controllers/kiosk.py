# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied
import json
import logging

_logger = logging.getLogger(__name__)


class BarberKioskController(http.Controller):
    """Controller for barber kiosk display"""

    def _check_kiosk_access(self, token=None):
        """
        Check if kiosk access is allowed
        
        Args:
            token: Optional access token from request
            
        Returns:
            dict: Kiosk settings if access allowed
            
        Raises:
            AccessDenied: If access is not allowed
        """
        kiosk_service = request.env['bp.barber.kiosk.service'].sudo()
        settings = kiosk_service.get_kiosk_settings()
        
        # Check if kiosk is enabled
        if not settings['public_enabled']:
            raise AccessDenied("Kiosk access is disabled")
        
        # Check token if required
        if settings['access_token']:
            if not token or token != settings['access_token']:
                raise AccessDenied("Invalid or missing access token")
        
        return settings

    @http.route('/barber/kiosk', type='http', auth='public', website=True)
    def kiosk_page(self, **kwargs):
        """
        Render the kiosk page
        
        Query parameters:
            token: Optional access token
        """
        try:
            token = kwargs.get('token')
            settings = self._check_kiosk_access(token)
            
            # Get company information
            company = request.env.company
            
            # Prepare template context
            context = {
                'company': company,
                'kiosk_token': settings['access_token'],
                'refresh_seconds': settings['refresh_seconds'],
                'base_url': request.httprequest.host_url.rstrip('/'),
            }
            
            return request.render('bp_barber_management.kiosk_page', context)
            
        except AccessDenied as e:
            return request.not_found(str(e))
        except Exception as e:
            _logger.error(f"Error in kiosk page: {e}")
            return request.not_found("Kiosk unavailable")

    @http.route('/barber/kiosk/data', type='json', auth='public', methods=['POST'])
    def kiosk_data_json(self, **kwargs):
        """
        Get kiosk data as JSON (POST method for JSON requests)
        
        JSON payload:
            company_id: Optional company ID
            barber_ids: Optional list of barber IDs
            token: Optional access token
        """
        try:
            # Get request data
            data = request.jsonrequest or {}
            token = data.get('token')
            
            # Check access
            self._check_kiosk_access(token)
            
            # Get parameters
            company_id = data.get('company_id')
            barber_ids = data.get('barber_ids')
            
            # Get kiosk service and data
            kiosk_service = request.env['bp.barber.kiosk.service'].sudo()
            result = kiosk_service.get_kiosk_data(
                company_id=company_id,
                barber_ids=barber_ids
            )
            
            return result
            
        except AccessDenied as e:
            return {'error': str(e), 'code': 'ACCESS_DENIED'}
        except Exception as e:
            _logger.error(f"Error in kiosk data JSON: {e}")
            return {'error': 'Internal server error', 'code': 'SERVER_ERROR'}

    @http.route('/barber/kiosk/data', type='http', auth='public', methods=['GET'])
    def kiosk_data_http(self, **kwargs):
        """
        Get kiosk data via HTTP GET (for testing and direct access)
        
        Query parameters:
            token: Optional access token
            company_id: Optional company ID
            barber_ids: Optional comma-separated barber IDs
        """
        try:
            token = kwargs.get('token')
            
            # Check access
            self._check_kiosk_access(token)
            
            # Parse parameters
            company_id = None
            if kwargs.get('company_id'):
                try:
                    company_id = int(kwargs.get('company_id'))
                except (ValueError, TypeError):
                    pass
            
            barber_ids = None
            if kwargs.get('barber_ids'):
                try:
                    barber_ids = [int(x.strip()) for x in kwargs.get('barber_ids').split(',') if x.strip()]
                except (ValueError, TypeError):
                    pass
            
            # Get kiosk service and data
            kiosk_service = request.env['bp.barber.kiosk.service'].sudo()
            result = kiosk_service.get_kiosk_data(
                company_id=company_id,
                barber_ids=barber_ids
            )
            
            return request.make_response(
                json.dumps(result, indent=2, default=str),
                headers={'Content-Type': 'application/json'}
            )
            
        except AccessDenied as e:
            return request.make_response(
                json.dumps({'error': str(e), 'code': 'ACCESS_DENIED'}),
                status=404,
                headers={'Content-Type': 'application/json'}
            )
        except Exception as e:
            _logger.error(f"Error in kiosk data HTTP: {e}")
            return request.make_response(
                json.dumps({'error': 'Internal server error', 'code': 'SERVER_ERROR'}),
                status=500,
                headers={'Content-Type': 'application/json'}
            )

    @http.route('/barber/kiosk/test', type='http', auth='public')
    def kiosk_test(self, **kwargs):
        """Test endpoint to verify kiosk controller is working"""
        try:
            token = kwargs.get('token')
            settings = self._check_kiosk_access(token)
            
            return f"""
            <html>
                <head><title>Barber Kiosk Test</title></head>
                <body>
                    <h1>Barber Kiosk Controller Test</h1>
                    <p>Controller is working!</p>
                    <p>Settings:</p>
                    <ul>
                        <li>Public Enabled: {settings['public_enabled']}</li>
                        <li>Token Required: {'Yes' if settings['access_token'] else 'No'}</li>
                        <li>Refresh Seconds: {settings['refresh_seconds']}</li>
                    </ul>
                    <p><a href="/barber/kiosk{f'?token={token}' if token else ''}">Open Kiosk</a></p>
                    <p><a href="/barber/kiosk/data{f'?token={token}' if token else ''}">Test Data Endpoint</a></p>
                </body>
            </html>
            """
            
        except AccessDenied as e:
            return f"<h1>Access Denied</h1><p>{e}</p>"
        except Exception as e:
            return f"<h1>Error</h1><p>{e}</p>"