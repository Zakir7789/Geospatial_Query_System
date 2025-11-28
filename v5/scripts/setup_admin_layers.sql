-- 1. Create Countries Table (Polygons)
CREATE TABLE IF NOT EXISTS countries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    iso_code VARCHAR(3),       -- e.g., 'USA', 'IND'
    continent VARCHAR(100),
    geom GEOMETRY(MultiPolygon, 4326) -- Stores the boundary shape
);

-- Index for fast "Which country is this point in?" queries
CREATE INDEX IF NOT EXISTS idx_countries_geom ON countries USING GIST(geom);

-- 2. Create States/Provinces Table (Polygons)
CREATE TABLE IF NOT EXISTS states (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    country_code VARCHAR(3),   -- Foreign key link to countries
    state_code VARCHAR(10),    -- e.g., 'CA', 'KA'
    geom GEOMETRY(MultiPolygon, 4326) -- Stores the boundary shape
);

-- Index for fast "Which state is this city in?" queries
CREATE INDEX IF NOT EXISTS idx_states_geom ON states USING GIST(geom);