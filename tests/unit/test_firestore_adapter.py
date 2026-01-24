import pytest
from unittest.mock import MagicMock, AsyncMock
import sys

# Mockear google.adk.sessions antes de importar el conector
sys.modules["google.adk.sessions"] = MagicMock()
# Ajustar el mock para que BaseSessionService exista como clase base
sys.modules["google.adk.sessions"].BaseSessionService = MagicMock
from app.services.adk_firestore_connector import FirestoreADKSessionService

@pytest.fixture
def mock_firestore_service(mocker):
    """Mock del servicio de Firestore subyacente."""
    mock = mocker.patch("app.services.adk_firestore_connector.get_firestore_service")
    mock_instance = mock.return_value
    
    # Configurar métodos asíncronos para que devuelvan futuros o corrutinas válidas
    # AsyncMock hace esto por defecto, pero a veces falla si no se configura explícitamente el return_value
    mock_instance.get_session = AsyncMock()
    mock_instance.save_session = AsyncMock()
    return mock_instance

@pytest.mark.asyncio
async def test_create_session(mock_firestore_service):
    service = FirestoreADKSessionService()
    session = await service.create_session(app_name="app", user_id="u1", session_id="s1")
    
    assert session.session_id == "s1"
    # Verificar que se llamó a save_session (awaitable)
    assert mock_firestore_service.save_session.call_count == 1

@pytest.mark.asyncio
async def test_get_session_exists(mock_firestore_service):
    # Configurar return_value como una corrutina resuelta para evitar problemas con AsyncMock/MagicMock mixtos
    session_data = {
        "app_name": "app",
        "user_id": "u1",
        "session_id": "s1",
        "history": [{"role": "user", "text": "Hola"}],
        "state": {"foo": "bar"}
    }
    # Forzar que el mock retorne data al ser waiteado
    mock_firestore_service.get_session.side_effect = None
    mock_firestore_service.get_session.return_value = session_data
    
    service = FirestoreADKSessionService()
    session = await service.get_session("app", "u1", "s1")
    
    assert session is not None
    assert session.session_id == "s1"
    # En ADK Session, history puede ser lista de objetos o dicts dependiendo mock, 
    # pero aquí validamos que se propagó la data.
    assert len(session.history) == 1

@pytest.mark.asyncio
async def test_get_session_not_exists(mock_firestore_service):
    mock_firestore_service.get_session.side_effect = None
    mock_firestore_service.get_session.return_value = None
    
    service = FirestoreADKSessionService()
    session = await service.get_session("app", "u1", "s1")
    
    assert session is None
