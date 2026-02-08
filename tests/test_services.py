import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.user_service import UserService
from app.models.user import User, UserRole

@pytest.mark.asyncio
async def test_get_by_telegram_id_found(mock_session):
    # Setup
    service = UserService(mock_session)
    mock_user = User(id="123", telegram_id=111, role=UserRole.CUSTOMER)
    
    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Act
    user = await service.get_by_telegram_id(111)

    # Assert
    assert user is not None
    assert user.telegram_id == 111
    mock_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_or_create_new_user(mock_session):
    # Setup
    service = UserService(mock_session)
    
    # Mock "not found" first
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Act
    user = await service.get_or_create(telegram_id=222, username="newuser")

    # Assert
    assert user.telegram_id == 222
    assert user.username == "newuser"
    assert user.role == UserRole.CUSTOMER
    
    # Verify add and commit were called
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
