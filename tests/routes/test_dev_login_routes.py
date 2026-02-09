"""
Unit tests for dev_login routes.
"""
import os
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from api_utils.routes.dev_login_routes import create_dev_login_routes
from api_utils.flask_utils.exceptions import HTTPNotFound
from api_utils import Config


class TestDevLoginRoutes(unittest.TestCase):
    """Test dev_login routes."""
    
    def setUp(self):
        """Set up test Flask app."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        Config._instance = None
        # Set JWT_SECRET before initializing config to avoid validation error
        os.environ['JWT_SECRET'] = 'test-secret-for-dev-login-tests'
        self.config = Config.get_instance()
        self.client = self.app.test_client()
    
    def test_dev_login_disabled_returns_404(self):
        """Test that dev login returns 404 when ENABLE_LOGIN is False (hides endpoint existence)."""
        with patch.object(self.config, 'ENABLE_LOGIN', False):
            self.app.register_blueprint(create_dev_login_routes(), url_prefix='/dev-login')
            response = self.client.post('/dev-login', json={})
            self.assertEqual(response.status_code, 404)
            # Should not reveal that the endpoint exists
            self.assertIn("not found", response.json['error'].lower())
    
    def test_dev_login_enabled_returns_token(self):
        """Test that dev login returns token when ENABLE_LOGIN is True."""
        with patch.object(self.config, 'ENABLE_LOGIN', True):
            self.app.register_blueprint(create_dev_login_routes(), url_prefix='/dev-login')
            response = self.client.post('/dev-login', json={})
            self.assertEqual(response.status_code, 200)
            self.assertIn('access_token', response.json)
            self.assertEqual(response.json['token_type'], 'bearer')
            self.assertIn('subject', response.json)
            self.assertIn('roles', response.json)
            self.assertIn('expires_at', response.json)
    
    def test_dev_login_with_default_values(self):
        """Test dev login with default subject and roles."""
        with patch.object(self.config, 'ENABLE_LOGIN', True):
            self.app.register_blueprint(create_dev_login_routes(), url_prefix='/dev-login')
            response = self.client.post('/dev-login', json={})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['subject'], 'dev-user-1')
            self.assertEqual(response.json['roles'], ['developer'])
    
    def test_dev_login_with_custom_values(self):
        """Test dev login with custom subject and roles."""
        with patch.object(self.config, 'ENABLE_LOGIN', True):
            self.app.register_blueprint(create_dev_login_routes(), url_prefix='/dev-login')
            response = self.client.post('/dev-login', json={
                'subject': 'custom-user',
                'roles': ['admin', 'user']
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['subject'], 'custom-user')
            self.assertEqual(response.json['roles'], ['admin', 'user'])
    
    def test_dev_login_uses_config_values(self):
        """Test that dev login uses JWT config values from Config."""
        with patch.object(self.config, 'ENABLE_LOGIN', True):
            with patch.object(self.config, 'JWT_SECRET', 'test-secret'):
                with patch.object(self.config, 'JWT_ALGORITHM', 'HS256'):
                    with patch.object(self.config, 'JWT_ISSUER', 'test-issuer'):
                        with patch.object(self.config, 'JWT_AUDIENCE', 'test-audience'):
                            with patch.object(self.config, 'JWT_TTL_MINUTES', 120):
                                self.app.register_blueprint(create_dev_login_routes(), url_prefix='/dev-login')
                                response = self.client.post('/dev-login', json={})
                                self.assertEqual(response.status_code, 200)
                                # Token should be valid and decodable
                                import jwt
                                token = jwt.decode(
                                    response.json['access_token'],
                                    options={"verify_signature": False}
                                )
                                self.assertEqual(token['iss'], 'test-issuer')
                                self.assertEqual(token['aud'], 'test-audience')
                                self.assertEqual(token['sub'], 'dev-user-1')
                                self.assertEqual(token['roles'], ['developer'])
    
    def test_dev_login_jwt_encoding_error(self):
        """Test that dev-login handles JWT encoding errors."""
        with patch.object(self.config, 'ENABLE_LOGIN', True):
            self.app.register_blueprint(create_dev_login_routes(), url_prefix='/dev-login')
            
            with patch('api_utils.routes.dev_login_routes.jwt.encode') as mock_encode:
                mock_encode.side_effect = Exception("JWT encoding failed")
                
                response = self.client.post('/dev-login', json={'subject': 'test-user'})
                
                self.assertEqual(response.status_code, 403)
                data = response.get_json()
                self.assertIn('error', data)
                self.assertIn('Error generating token', data['error'])
    
    def test_dev_login_options_method(self):
        """Test OPTIONS method for CORS preflight."""
        with patch.object(self.config, 'ENABLE_LOGIN', True):
            self.app.register_blueprint(create_dev_login_routes(), url_prefix='/dev-login')
            
            response = self.client.options('/dev-login')
            
            self.assertEqual(response.status_code, 200)
            self.assertIn('Access-Control-Allow-Origin', response.headers)
            self.assertEqual(response.headers['Access-Control-Allow-Origin'], '*')
            self.assertIn('Access-Control-Allow-Methods', response.headers)
            self.assertIn('Access-Control-Allow-Headers', response.headers)


if __name__ == '__main__':
    unittest.main()

