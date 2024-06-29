CREATE TABLE sensor (
    id SERIAL PRIMARY KEY,
    temperature float NOT NULL,
    heure TIMESTAMP NOT NULL,
    etat varchar(50) null
);