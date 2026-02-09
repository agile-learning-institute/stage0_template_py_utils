"""
Pytest configuration for api_utils tests.

This file is automatically loaded by pytest before running tests.
It sets up necessary environment variables for testing.
"""
import os

# Set JWT_SECRET at module import time (before any tests run)
# This prevents ValueError when Config is initialized during test setup
# Individual tests can override this by setting JWT_SECRET before calling Config.get_instance()
if 'JWT_SECRET' not in os.environ:
    os.environ['JWT_SECRET'] = 'test-secret-for-testing'
