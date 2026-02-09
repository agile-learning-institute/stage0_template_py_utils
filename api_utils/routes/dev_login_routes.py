"""
Dev Login routes for Flask services.

Provides a /dev-login endpoint that issues signed JWTs for local / dev environments.
This endpoint is only enabled when Config.ENABLE_LOGIN is True.

Security model:
- Endpoint is only enabled when Config.ENABLE_LOGIN is True
- Endpoint path is /dev-login and should NOT be reverse-proxied in production
- The reverse proxy only covers /api/* endpoints, so this endpoint is not visible
  when networking prevents direct access
"""
from flask import Blueprint, jsonify, request
from api_utils.config.config import Config
from api_utils.flask_utils.route_wrapper import handle_route_exceptions
from api_utils.flask_utils.exceptions import HTTPNotFound, HTTPForbidden
from datetime import datetime, timedelta, timezone
import jwt

import logging
logger = logging.getLogger(__name__)


def create_dev_login_routes():
    """
    Create a Flask Blueprint for dev-login endpoint.
    
    This endpoint issues signed JWTs for local / dev environments.
    The endpoint always returns a blueprint, but will return 404 when
    Config.ENABLE_LOGIN is False (security: hides endpoint existence).
    
    Returns:
        Blueprint: Flask Blueprint with dev-login route (always returned)
        
    Example usage:
        from api_utils import create_dev_login_routes
        app.register_blueprint(create_dev_login_routes(), url_prefix='/dev-login')
    """
    dev_login_routes = Blueprint('dev_login_routes', __name__)
    config = Config.get_instance()
    
    @dev_login_routes.route('', methods=['POST', 'OPTIONS'])
    @handle_route_exceptions
    def dev_login():
        """
        POST /dev-login - Issue a signed JWT for development.
        
        Request body (JSON, all fields optional):
        {
            "subject": "dev-user-1",  # Default: "dev-user-1"
            "roles": ["developer", "admin"]  # Default: ["developer"]
        }
        
        Returns:
            JSON response with access_token and metadata
        """
        # Handle CORS preflight requests
        if request.method == 'OPTIONS':
            response = jsonify({})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            return response, 200
        
        # Check if dev login is enabled
        # Return 404 instead of 403 to hide endpoint existence when disabled
        if not config.ENABLE_LOGIN:
            raise HTTPNotFound("Not found")
        
        # Get request data (minimal: only subject and roles)
        data = request.get_json() or {}
        subject = data.get('subject', 'dev-user-1')
        roles = data.get('roles', ['developer'])
        
        # Build JWT claims (minimal set)
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=config.JWT_TTL_MINUTES)
        
        claims = {
            "iss": config.JWT_ISSUER,
            "aud": config.JWT_AUDIENCE,
            "sub": subject,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "roles": roles
        }
        
        # Generate JWT
        try:
            token = jwt.encode(
                claims,
                config.JWT_SECRET,
                algorithm=config.JWT_ALGORITHM
            )
        except Exception as e:
            logger.error(f"Error encoding JWT: {str(e)}")
            raise HTTPForbidden(f"Error generating token: {str(e)}")
        
        # Return response with CORS headers
        response = {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": exp.isoformat(),
            "subject": subject,
            "roles": roles
        }
        
        logger.info(f"Dev login successful for subject: {subject}")
        response_obj = jsonify(response)
        response_obj.headers.add('Access-Control-Allow-Origin', '*')
        response_obj.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response_obj.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        return response_obj, 200
    
    logger.info("Dev Login Flask Routes Registered")
    return dev_login_routes

