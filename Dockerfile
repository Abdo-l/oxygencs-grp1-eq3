# Utilisation d'une image Python officielle comme base
FROM python:3.8-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier les fichiers nécessaires dans le conteneur
COPY Pipfile Pipfile.lock /app/
COPY src /app/src
#COPY .env /app/.env
COPY configmap.yaml /app/configmap.yaml
# Installer les dépendances en utilisant Pipenv
RUN pip install pipenv
RUN pipenv install --deploy --ignore-pipfile

# Installer python-dotenv pour charger les variables d'environnement
#RUN pipenv install python-dotenv

# Commande pour exécuter l'application
CMD ["pipenv", "run", "start"]
