"""
Tests d'intégration pour l'application Oxygen CS.
"""

import os
import json
from unittest.mock import patch, MagicMock
import pytest
import psycopg2
from src.main import App


@pytest.fixture
def app_fixture():
    """
    Fixture pour initialiser l'application avant chaque test et fermer
    la connexion à la base de données après chaque test.
    """
    app = App()
    yield app
    app.connection.close()


@pytest.fixture
def db_fixture():
    """
    Fixture pour créer une connexion temporaire à la base de données pour les tests.
    """
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
    )
    yield conn
    conn.close()


def test_db_connection(app_fixture):
    """
    Vérifie que la connexion à la base de données est établie correctement.
    """
    assert app_fixture.connection is not None
    cursor = app_fixture.connection.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    assert result[0] == 1


@patch("src.main.requests.get")
def test_send_action_to_hvac(mock_get, app_fixture):
    """
    Teste l'envoi d'une action au service HVAC.
    """
    mock_response = MagicMock()
    mock_response.text = json.dumps({"Response": "Success"})
    mock_get.return_value = mock_response

    response = app_fixture.send_action_to_hvac("TurnOnAc")
    assert response == "Success"
    mock_get.assert_called_once_with(
        f"{app_fixture.host}/api/hvac/{app_fixture.token}/TurnOnAc/{app_fixture.ticks}",
        timeout=10,
    )


def test_save_event_to_database(app_fixture):
    """
    Teste l'enregistrement des événements de capteurs dans la base de données.
    """
    timestamp = "2024-06-28 12:00:00.000"
    temperature = 25.5
    etat = "TurnOnAc"
    app_fixture.save_event_to_database(timestamp, temperature, etat)

    cursor = app_fixture.connection.cursor()
    cursor.execute(
        "SELECT temperature, heure, etat FROM sensor WHERE heure = %s", (timestamp,)
    )
    result = cursor.fetchone()
    print("--------------------------------")
    print(result[0])
    print("--------------------------------")
    assert result[0] == (temperature)
    assert result[2] == (etat)