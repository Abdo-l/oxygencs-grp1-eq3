import os
import logging
import json
import time

import psycopg2
from signalrcore.hub_connection_builder import HubConnectionBuilder
import requests


class App:

    def __init__(self):

        self._hub_connection = None
        self.TICKS = 10

        # À configurer par votre équipe
        self.HOST = os.getenv("HOST")  # Configurez votre hôte ici
        self.TOKEN = os.getenv("TOKEN")  # Configurez votre jeton ici
        self.T_MAX = os.getenv("T_MAX")  # Configurez votre température maximale ici
        self.T_MIN = os.getenv("T_MIN")  # Configurez votre température minimale ici

        try:
            self.connection = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                port=os.getenv("DB_PORT"),
            )
        except psycopg2.Error as e:
            print("Erreur de connexion à la base de données : ", e)

    def __del__(self):
        if self._hub_connection != None:
            self._hub_connection.stop()

    def start(self):
        """Start Oxygen CS."""
        self.setup_sensor_hub()
        self._hub_connection.start()
        print("Press CTRL+C to exit.")
        while True:
            time.sleep(2)

    def setup_sensor_hub(self):
        """Configure hub connection and subscribe to sensor data events."""
        self._hub_connection = (
            HubConnectionBuilder()
            .with_url(f"{self.HOST}/SensorHub?token={self.TOKEN}")
            .configure_logging(logging.INFO)
            .with_automatic_reconnect(
                {
                    "type": "raw",
                    "keep_alive_interval": 10,
                    "reconnect_interval": 5,
                    "max_attempts": 999,
                }
            )
            .build()
        )
        self._hub_connection.on("ReceiveSensorData", self.on_sensor_data_received)
        self._hub_connection.on_open(lambda: print("||| Connection opened."))
        self._hub_connection.on_close(lambda: print("||| Connection closed."))
        self._hub_connection.on_error(
            lambda data: print(f"||| An exception was thrown closed: {data.error}")
        )

    def on_sensor_data_received(self, data):
        """Callback method to handle sensor data on reception."""
        try:
            print(data[0]["date"] + " --> " + data[0]["data"], flush=True)
            timestamp = data[0]["date"]
            temperature = float(data[0]["data"])
            etat = self.take_action(temperature)
            self.save_event_to_database(timestamp, temperature, etat)
        except Exception as err:  # pylint: disable=broad-except
            print(err)

    def take_action(self, temperature):
        """Take action to HVAC depending on current temperature."""
        if float(temperature) >= float(self.T_MAX):
            self.send_action_to_hvac("TurnOnAc")
        elif float(temperature) <= float(self.T_MIN):
            self.send_action_to_hvac("TurnOnHeater")

    def send_action_to_hvac(self, action):
        """Send action query to the HVAC service."""
        r = requests.get(f"{self.HOST}/api/hvac/{self.TOKEN}/{action}/{self.TICKS}")
        details = json.loads(r.text)
        print(details, flush=True)

    def save_event_to_database(self, timestamp, temperature, etat):
        """Save sensor data into database."""
        try:
            cur = self.connection.cursor()
            cur.execute(
                "INSERT INTO sensor (temperature, heure, etat)"
                + "VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
                (temperature, timestamp, etat),
            )
            self.connection.commit()
            cur.close()
        except psycopg2.Error as e:
            print("Erreur lors de l'enregistrement dans la base de données : ", e)



if __name__ == "__main__":
    app = App()
    app.start()
