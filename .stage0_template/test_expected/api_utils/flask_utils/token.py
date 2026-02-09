"""
Token utilities for Flask requests.

Provides Token class that extracts and validates JWT tokens from request headers,
and a helper function for backward compatibility.
"""
from flask import request
import jwt
from datetime import datetime, timezone
from api_utils.flask_utils.exceptions import HTTPUnauthorized
from api_utils.config.config import Config

import logging
logger = logging.getLogger(__name__)


class Token:
    """
    Token class that extracts and validates JWT tokens from HTTP request headers.
    
    The Token is constructed from the Authorization header and provides:
    - Token claims (user_id, roles, email, etc.)
    - Request metadata (remote IP)
    
    Raises HTTPUnauthorized exception if:
    - Token is missing
    - Token is invalid
    - Token is expired
    - Token signature verification fails
    
    Example:
        token = Token()
        user_id = token.claims.get('sub')
        roles = token.claims.get('roles', [])
        remote_ip = token.remote_ip
    """
    
    def __init__(self, request_obj=None):
        """
        Initialize Token from Flask request.
        
        Args:
            request_obj: Flask request object (defaults to flask.request)
            
        Raises:
            HTTPUnauthorized: If token is missing, invalid, or expired
        """
        if request_obj is None:
            request_obj = request
        
        self.request = request_obj
        self.remote_ip = request_obj.remote_addr
        self.claims = {}
        
        # Extract token from Authorization header
        auth_header = request_obj.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            logger.warning("Missing or invalid Authorization header")
            raise HTTPUnauthorized("Missing or invalid Authorization header")
        
        token_string = auth_header[7:].strip()  # Remove "Bearer " prefix
        
        if not token_string:
            logger.warning("Empty token in Authorization header")
            raise HTTPUnauthorized("Empty token in Authorization header")
        
        # Decode and validate token
        try:
            config = Config.get_instance()
            try:
                if config.JWT_SECRET:
                    # Verify signature with the configured secret
                    self.claims = jwt.decode(
                        token_string,
                        config.JWT_SECRET,
                        algorithms=[config.JWT_ALGORITHM],
                        audience=config.JWT_AUDIENCE,
                        issuer=config.JWT_ISSUER,
                    )
                else:
                    # No secret configured: decode without signature verification (development only)
                    self.claims = jwt.decode(
                        token_string,
                        options={"verify_signature": False}
                    )
                    
                    if 'exp' in self.claims:
                        exp_timestamp = self.claims['exp']
                        current_timestamp = int(datetime.now(timezone.utc).timestamp())
                        if current_timestamp >= exp_timestamp:
                            logger.warning("Token has expired")
                            raise HTTPUnauthorized("Token has expired")
                
            except jwt.ExpiredSignatureError:
                logger.warning("Token has expired")
                raise HTTPUnauthorized("Token has expired")
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid token: {str(e)}")
                raise HTTPUnauthorized(f"Invalid token: {str(e)}")
            
            self._map_claims()
            
        except HTTPUnauthorized:
            raise
        except Exception as e:
            logger.error(f"Error decoding token: {str(e)}")
            raise HTTPUnauthorized(f"Error decoding token: {str(e)}")
    
    def _map_claims(self):
        """
        Map JWT claims to expected internal format.
        
        Maps standard JWT claims (sub, email, roles, etc.) to the format
        expected by the rest of the application.
        """
        # Map 'sub' claim to 'user_id' for backward compatibility
        if 'sub' in self.claims:
            self.claims['user_id'] = self.claims['sub']
        
        # Ensure roles is a list
        if 'roles' in self.claims and not isinstance(self.claims['roles'], list):
            # If roles is a string, try to parse it
            if isinstance(self.claims['roles'], str):
                self.claims['roles'] = [role.strip() for role in self.claims['roles'].split(',')]
            else:
                self.claims['roles'] = []
        elif 'roles' not in self.claims:
            self.claims['roles'] = []
    
    def to_dict(self):
        """
        Convert token to dictionary format.
        
        Returns:
            dict: Token information including claims and metadata (minimal set)
        """
        return {
            "user_id": self.claims.get('user_id', self.claims.get('sub', '')),
            "roles": self.claims.get('roles', []),
            "remote_ip": self.remote_ip
        }


def create_flask_token():
    """
    Create a token dictionary from the JWT in the request.
    
    This is a backward-compatible function that creates a Token instance
    and returns its dictionary representation.
    
    Returns:
        dict: Token information with user_id and roles
        
    Raises:
        HTTPUnauthorized: If token is missing, invalid, or expired
    """
    token = Token()
    return token.to_dict()

