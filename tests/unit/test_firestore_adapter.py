import pytest
from unittest.mock import MagicMock, AsyncMock
import sys

# sys.modules removal - using real package
from app.services.adk_firestore_connector import FirestoreADKSessionService

@pytest.fixture
def mock_firestore_service(mocker):
    """Mock del servicio de Firestore subyacente."""
    mock = mocker.patch("app.services.adk_firestore_connector.get_firestore_service")
    # Configurar el objeto retornado por get_firestore_service()
    mock_instance = mock.return_value
    
    # Asignar AsyncMocks explícitos a los métodos que se van a llamar con await
    mock_instance.get_session = AsyncMock()
    mock_instance.save_session = AsyncMock()
    
    return mock_instance

@pytest.mark.asyncio
async def test_create_session(mock_firestore_service):
    service = FirestoreADKSessionService()
    session = await service.create_session(app_name="app", user_id="u1", session_id="s1")
    
    assert session.id == "s1"
    # Verificar que se llamó a save_session (awaitable)
    assert mock_firestore_service.save_session.call_count == 1

@pytest.mark.asyncio
async def test_get_session_exists(mock_firestore_service):
    # Configurar return_value como una corrutina resuelta
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
    session = await service.get_session(app_name="app", user_id="u1", session_id="s1")
    
    assert session is not None
    assert session.id == "s1"
    # Ahora history viene de la DB validado y mappeado a events
    assert len(session.events) == 1

@pytest.mark.asyncio
async def test_get_session_not_exists(mock_firestore_service):
    mock_firestore_service.get_session.side_effect = None
    mock_firestore_service.get_session.return_value = None
    
    service = FirestoreADKSessionService()
    session = await service.get_session(app_name="app", user_id="u1", session_id="s1")
    
    assert session is None
