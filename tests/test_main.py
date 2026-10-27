import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from app.main import app

@pytest.mark.asyncio
async def test_get_recommendations_success(mocker):
    """Тестируем успешный случай: товар найден, рекомендации выданы"""

    # Имитация ответов PostgreSQL (целевой товар и список похожих)
    mock_product = {'category_id': 1, 'id': 7}

    mock_recommendations = [
        {'id': 5, 'name': 'Смартфон Samsung Galaxy S25 Ultra', 'price': 140000.00, 'image': 'img1.png', 'category_id': 1, 'slug': 'smartfon-samsung-galaxy-s25-ultra'},
        {'id': 11, 'name': 'Смартфон Google Pixel 8', 'price': 75000.00, 'image': 'img2.png', 'category_id': 1, 'slug': 'smartfon-google-pixel-8'},
    ]

    # Настройка асинхронных методов fetchrow и fetch
    mock_connection = AsyncMock()
    mock_connection.fetchrow.return_value = mock_product
    mock_connection.fetch.return_value = mock_recommendations

    # Мокаем контекстный менеджер подключения 'async with pool.acquire()'
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
    app.state.db_pool = mock_pool

    # Вызов эндпоинта через асинхронный HTTP-клиент
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as ac:
        response = await ac.get('/recommendations/test-smartphone')

    # Проверка статус-кода и структуры JSON-ответа
    assert response.status_code == 200

    json_data = response.json()
    assert len(json_data) == 2
    assert json_data[0]['name'] == 'Смартфон Samsung Galaxy S25 Ultra'
    assert json_data[1]['slug'] == 'smartfon-google-pixel-8'

    # Проверка, что SQL-запрос был выполнен с правильным slug
    mock_connection.fetchrow.assert_called_once_with(
        'SELECT category_id, id FROM products WHERE slug = $1;', 'test-smartphone'
    )


@pytest.mark.asyncio
async def test_get_recommendations_not_found(mocker):
    """Тестируем сценарий 404: когда товара с таким slug нет в базе"""

    # Имитируем, что PostgreSQL вернул None (товар не найден)
    isolated_connection = AsyncMock()
    isolated_connection.fetchrow.return_value = None

    # Мокаем контекстный менеджер подключения 'async with pool.acquire()'
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = isolated_connection

    app.state.db_pool = mock_pool

    # Вызов эндпоинта через асинхронный HTTP-клиент
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as ac:
        responce = await ac.get('/recommendations/unknown-slug')

    # Проверка статус-кода 404 и текста ошибки
    assert responce.status_code == 404
    assert responce.json()['detail'] == 'Товар не найден'
