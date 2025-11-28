-- scripts/setup_full_db.sql

-- 1. Enable Extensions (REQUIRED for your indexes)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- Required for gin_trgm_ops

-- 2. Clean Slate (Drop existing tables)
DROP TABLE IF EXISTS cities CASCADE;
DROP TABLE IF EXISTS states CASCADE;
DROP TABLE IF EXISTS countries CASCADE;

-- 3. Create COUNTRIES Table
CREATE TABLE countries (
    country_id SERIAL PRIMARY KEY,
    iso_code VARCHAR(10),
    country_name TEXT UNIQUE,
    capital TEXT,
    continent TEXT,
    population BIGINT,
    area_sq_km DOUBLE PRECISION,
    currency TEXT,
    geom GEOMETRY(MultiPolygon, 4326)
);
-- Indexes
CREATE INDEX idx_countries_geom ON countries USING GIST(geom);
CREATE INDEX idx_countries_name ON countries USING GIN(country_name gin_trgm_ops);

-- 4. Create STATES Table
CREATE TABLE states (
    state_id SERIAL PRIMARY KEY,
    country_code VARCHAR(10) NOT NULL,
    state_code VARCHAR(50),
    state_name TEXT NOT NULL,
    geonameid BIGINT,
    geom GEOMETRY(MultiPolygon, 4326)
);
-- Indexes
CREATE INDEX idx_state_country ON states(country_code);
CREATE INDEX idx_states_geom ON states USING GIST(geom);
CREATE INDEX idx_states_name ON states USING GIN(state_name gin_trgm_ops);

-- 5. Create CITIES Table
CREATE TABLE cities (
    city_id SERIAL PRIMARY KEY,
    city_name TEXT,
    alt_names TEXT[], -- Array of strings for aliases like 'NYC', 'Bombay'
    country_code VARCHAR(10),
    state_code VARCHAR(50),
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    population BIGINT,
    geom GEOMETRY(Point, 4326)
);
-- Indexes
CREATE INDEX idx_cities_geom ON cities USING GIST(geom);
CREATE INDEX idx_cities_name ON cities USING GIN(city_name gin_trgm_ops);
CREATE INDEX idx_city_country ON cities(country_code);