import importlib
import os

import pytest

from src.app.service.webex_service import WebexService


@pytest.mark.unit
@pytest.mark.fast
def test_webex_service_reads_required_env_vars_from_runtime_environment():
    required_vars = [
        "WEBEX_CLIENT_ID",
        "WEBEX_CLIENT_SECRET",
        "WEBEX_REDIRECT_URI",
    ]

    missing_vars = [name for name in required_vars if not os.getenv(name)]
    assert not missing_vars, (
        "Missing required Webex environment variables: "
        + ", ".join(sorted(missing_vars))
    )

    service = WebexService()

    assert service.client_id == os.getenv("WEBEX_CLIENT_ID")
    assert service.client_secret == os.getenv("WEBEX_CLIENT_SECRET")
    assert service.redirect_uri == os.getenv("WEBEX_REDIRECT_URI")


@pytest.mark.unit
@pytest.mark.fast
def test_main_reads_required_env_vars_from_runtime_environment():
    required_vars = [
        "FLASK_SECRET_KEY",
        "JWT_SECRET_KEY",
        "SQLALCHEMY_DATABASE_URI",
    ]

    missing_vars = [name for name in required_vars if not os.getenv(name)]
    assert not missing_vars, (
        "Missing required main environment variables: "
        + ", ".join(sorted(missing_vars))
    )

    import src.app.main as app_main
    app_main = importlib.reload(app_main)

    assert app_main.application.config["SECRET_KEY"] == os.getenv("FLASK_SECRET_KEY")
    assert app_main.application.config["JWT_SECRET_KEY"] == os.getenv("JWT_SECRET_KEY")

    expected_db_uri = os.getenv("SQLALCHEMY_DATABASE_URI")
    assert app_main.application.config["SQLALCHEMY_DATABASE_URI"] == expected_db_uri


@pytest.mark.unit
@pytest.mark.fast
def test_runtime_environment_contains_required_deployment_vars():
    required_vars = [
        "WEBEX_CLIENT_ID",
        "WEBEX_CLIENT_SECRET",
        "WEBEX_REDIRECT_URI",
        "FLASK_SECRET_KEY",
        "JWT_SECRET_KEY",
        "SQLALCHEMY_DATABASE_URI",
    ]

    missing_vars = [name for name in required_vars if not os.environ.get(name)]

    assert not missing_vars, (
        "Missing required environment variables: "
        + ", ".join(sorted(missing_vars))
    )