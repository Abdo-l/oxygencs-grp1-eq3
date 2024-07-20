"""
Module principal pour l'application Oxygen CS.

Ce module contient la classe principale App qui gère la connexion au hub de capteurs,
la gestion des données de capteurs et les interactions avec un service HVAC.
"""

import os
import logging
import json
import time
import yaml
import psycopg2
from signalrcore.hub_connection_builder import HubConnectionBuilder
import requests


class App:
    """
    Classe principale de l'application Oxygen CS.

    Attributes:
        host (str): Hôte pour la configuration.
        token (str): Jeton pour l'authentification.
        t_max (str): Température maximale configurée.
        t_min (str): Température minimale configurée.
        connection: Connexion à la base de données PostgreSQL.
        _hub_connection: Connexion au hub de capteurs.
    """

    def __init__(self):
        """
        Initialise l'application avec la configuration et la connexion à la base de données.
        """
        self._hub_connection = None
        self.ticks = 10
        with open('configmap.yaml','r', encoding='utf-8') as file :
            config_map = yaml.safe_load(file)
        temp_conf = config_map['data']

        # À configurer par votre équipe
        self.host = os.getenv("HOST")  # Configurez votre hôte ici
        self.token = os.getenv("TOKEN")  # Configurez votre jeton ici
        self.t_max = temp_conf['T_MAX']  # Configurez votre température maximale ici
        self.t_min = temp_conf['T_MIN']  # Configurez votre température minimale ici

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
        """
        Arrête la connexion au hub lorsque l'application est supprimée.
        """
        if self._hub_connection is not None:
            self._hub_connection.stop()

    def start(self):
        """
        Lance l'application Oxygen CS.
        """
        self.setup_sensor_hub()
        self._hub_connection.start()
        print("Appuyez sur CTRL+C pour quitter.")
        while True:
            time.sleep(2)

    def setup_sensor_hub(self):
        """
        Configure la connexion au hub de capteurs et s'abonne aux événements de données de capteurs.
        """
        self._hub_connection = (
            HubConnectionBuilder()
            .with_url(f"{self.host}/SensorHub?token={self.token}")
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
        self._hub_connection.on_open(lambda: print("||| Connexion ouverte."))
        self._hub_connection.on_close(lambda: print("||| Connexion fermée."))
        self._hub_connection.on_error(
            lambda data: print(f"||| Une exception a été levée : {data.error}")
        )

    def on_sensor_data_received(self, data):
        """
        Méthode de rappel pour gérer les données de capteurs reçues.
        """
        try:
            print(data[0]["date"] + " --> " + data[0]["data"], flush=True)
            timestamp = data[0]["date"]
            temperature = float(data[0]["data"])
            etat = self.take_action(temperature)
            self.save_event_to_database(timestamp, temperature, etat)
        except Exception as err:  # pylint: disable=broad-except
            print(err)

    def take_action(self, temperature):
        """
        Prend des mesures HVAC en fonction de la température actuelle.
        """
        if float(temperature) >= float(self.t_max):
            return self.send_action_to_hvac("TurnOnAc")
        if float(temperature) <= float(self.t_min):
            return self.send_action_to_hvac("TurnOnHeater") + self.t_min
        return None

    def send_action_to_hvac(self, action):
        """
        Envoie une requête d'action au service HVAC.
        """
        try:
            r = requests.get(
                f"{self.host}/api/hvac/{self.token}/{action}/{self.ticks}", timeout=10
            )
            details = json.loads(r.text)
            print(details, flush=True)
            return details["Response"]
        except requests.RequestException as e:
            print(f"Erreur lors de l'envoi de l'action HVAC : {e}")
            return None

    def save_event_to_database(self, timestamp, temperature, etat):
        """
        Enregistre les données de capteurs dans la base de données.
        """
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
