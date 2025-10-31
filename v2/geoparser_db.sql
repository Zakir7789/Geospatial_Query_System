CREATE DATABASE geoparser;
-- connect to geoparser
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for trigram indexes

-- Countries
CREATE TABLE countries (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  iso_code CHAR(3),
  alt_names TEXT[],
  geom GEOMETRY
);

-- States
CREATE TABLE states (
  id SERIAL PRIMARY KEY,
  country_id INT REFERENCES countries(id),
  name TEXT NOT NULL,
  alt_names TEXT[],
  geom GEOMETRY
);

-- Cities
CREATE TABLE cities (
  id SERIAL PRIMARY KEY,
  country_id INT REFERENCES countries(id),
  state_id INT,
  name TEXT NOT NULL,
  alt_names TEXT[],
  population BIGINT,
  geom GEOMETRY
);

-- Aliases
CREATE TABLE aliases (
  id SERIAL PRIMARY KEY,
  alias TEXT NOT NULL,
  canonical_table TEXT NOT NULL, -- 'countries'|'states'|'cities'
  canonical_id INT NOT NULL,
  source TEXT,
  created_at TIMESTAMP DEFAULT now()
);
