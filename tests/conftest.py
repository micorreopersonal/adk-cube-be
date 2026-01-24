import pytest
import sys
import os

# Asegurar que el directorio raíz del proyecto está en el PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

@pytest.fixture
def mock_settings(mocker):
    """Mock de las variables de entorno para evitar leer .env real."""
    mocker.patch("app.core.config.Settings", return_value={
        "PROJECT_ID": "test-project",
        "BQ_DATASET": "test_dataset",
        "BQ_TABLE_TURNOVER": "test_table",
        "SECRET_KEY": "test_secret_key"
    })
