-- 1. Drop existing broken tables (Clean Slate)
DROP TABLE IF EXISTS states;
DROP TABLE IF EXISTS countries;

-- 2. Recreate Countries Table (With ALL columns)
CREATE TABLE countries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    iso_code VARCHAR(10),
    continent VARCHAR(100),
    geom GEOMETRY(MultiPolygon, 4326)
);
CREATE INDEX idx_countries_geom ON countries USING GIST(geom);

-- 3. Recreate States Table
CREATE TABLE states (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    country_code VARCHAR(10),
    state_code VARCHAR(10),
    geom GEOMETRY(MultiPolygon, 4326)
);
CREATE INDEX idx_states_geom ON states USING GIST(geom);