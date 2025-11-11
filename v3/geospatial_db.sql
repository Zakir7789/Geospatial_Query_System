-- Create the new database
CREATE DATABASE geospatial_db;

-- Connect to the new database
\c geospatial_db

-- === 1. ENABLE EXTENSIONS ===
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- === 2. CREATE A UNIFIED LOCATIONS TABLE ===
CREATE TYPE location_type AS ENUM ('COUNTRY', 'STATE', 'CITY');

CREATE TABLE countries (
    country_id SERIAL PRIMARY KEY,
    iso_code VARCHAR(10),
    country_name TEXT UNIQUE,
    capital TEXT,
    continent TEXT,
    population BIGINT,
    area_sq_km FLOAT,
    currency TEXT
);

CREATE TABLE states (
    state_id SERIAL PRIMARY KEY,
    country_code VARCHAR(10) NOT NULL,
    state_code VARCHAR(50),
    state_name TEXT NOT NULL,
    geonameid BIGINT
);

CREATE TABLE cities (
    city_id SERIAL PRIMARY KEY,
    city_name TEXT,
    alt_names TEXT[],
    country_code VARCHAR(10),
    state_code VARCHAR(50),
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    population BIGINT
);


-- === 3. CREATE INDEXES ===
CREATE INDEX idx_countries_name ON countries USING gin (country_name gin_trgm_ops);
CREATE INDEX idx_states_name ON states USING gin (state_name gin_trgm_ops);
CREATE INDEX idx_cities_name ON cities USING gin (city_name gin_trgm_ops);

CREATE INDEX idx_city_country ON cities(country_code);
CREATE INDEX idx_state_country ON states(country_code);
