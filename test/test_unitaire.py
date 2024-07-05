import os
import json
import unittest
from unittest.mock import patch, MagicMock, call
import psycopg2
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from main import App  # Assurez-vous que ce chemin est correct

class TestApp(unittest.TestCase):

    @patch('psycopg2.connect')
    @patch('os.getenv')
    def setUp(self, mock_getenv, mock_connect):
        # Mock des variables d'environnement
        mock_getenv.side_effect = lambda key: {
            "HOST": "http://159.203.50.162",
            "TOKEN": "544c14cc5eef61137a1d",
            "T_MAX": "25",
            "T_MIN": "21",
            "DB_HOST": "157.230.69.113",
            "DB_NAME": "db01eq3",
            "DB_USER": "user01eq3",
            "DB_PASSWORD": "Qm1zs9Pct7qckJZz",
            "DB_PORT": "5432",
        }.get(key)

        # Mock de la connexion à la base de données
        self.mock_connection = mock_connect.return_value
        self.app = App()
    def test_initialization(self):
    
      # Vérification que les attributs de l'application sont initialisés correctement avec les valeurs des variables d'environnement.

        self.assertEqual(self.app.host, "http://159.203.50.162")
        self.assertEqual(self.app.token, "544c14cc5eef61137a1d")
        self.assertEqual(self.app.t_max, "25")
        self.assertEqual(self.app.t_min, "21")
        self.assertIsNotNone(self.app.connection)

    @patch('signalrcore.hub_connection_builder.HubConnectionBuilder')
    def test_setup_sensor_hub(self, mock_hub_builder):

      #   Vérification que la connexion au hub de capteurs est correctement configurée. Validation que les méthodes critiques (on, on_open, on_close, on_error) sont appelées correctement.
        mock_hub = mock_hub_builder.return_value.build.return_value
        self.app.setup_sensor_hub()
        self.assertIsNotNone(self.app._hub_connection)
        
        expected_calls = [
            call.on("ReceiveSensorData", self.app.on_sensor_data_received),
            call.on_open(lambda: print("||| Connexion ouverte.")),
            call.on_close(lambda: print("||| Connexion fermée.")),
            call.on_error(lambda data: print(f"||| Une exception a été levée : {data.error}"))
        ]
        
        mock_hub.has_calls(expected_calls, any_order=True)

    @patch('requests.get')
    def test_send_action_to_hvac(self, mock_get):

     #    Simulation de la requête HTTP et vérification que l'action est correctement envoyée et que la réponse est traitée comme attendu.

        mock_response = MagicMock()
        mock_response.text = json.dumps({"Response": "Success"})
        mock_get.return_value = mock_response

        response = self.app.send_action_to_hvac("TurnOnAc")
        self.assertEqual(response, "Success")
        mock_get.assert_called_once_with(
            f"{self.app.host}/api/hvac/{self.app.token}/TurnOnAc/{self.app.ticks}",
            timeout=10,
        )

    @patch('psycopg2.connect')
    def test_save_event_to_database(self, mock_connect):

      #    Vérification que les événements sont correctement enregistrés dans la base de données en utilisant des mocks.
      
        mock_cursor = self.mock_connection.cursor.return_value

        self.app.save_event_to_database("2024-07-01T12:00:00", 25.0, "ActionSent")
        mock_cursor.execute.assert_called_with(
            "INSERT INTO sensor (temperature, heure, etat)"
            + "VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (25.0, "2024-07-01T12:00:00", "ActionSent"),
        )
        self.mock_connection.commit.assert_called_once()
        mock_cursor.close.assert_called_once()

if __name__ == "__main__":
    unittest.main()
