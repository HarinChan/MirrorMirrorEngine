"""
Test for existence of required env variables. 
This is just a check check if they exist, graceful error handling of the services
that require them should still be tested elsewhere.
"""
import os
import pytest


REQUIRED_ENV_VARS =[
    "FLASK_SECRET_KEY",
    "JWT_SECRET_KEY",
    "WEBEX_CLIENT_ID",
    "WEBEX_CLIENT_SECRET",
    "WEBEX_REDIRECT_URI"
]

@pytest.mark.parametrize("var_name", REQUIRED_ENV_VARS)
def test_env_var_exists(var_name):
    """
    Test that the required environment variables are set.
    """
    assert var_name in os.environ, f"Environment variable '{var_name}' is not set."
    assert os.environ.get(var_name) != "", f"Environment variable '{var_name}' is empty."