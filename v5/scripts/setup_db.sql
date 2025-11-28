-- 1. Enable PostGIS Extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Create the Table
CREATE TABLE IF NOT EXISTS cities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    country VARCHAR(255),
    population INTEGER,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION
);

-- 3. Add Geometry Column
ALTER TABLE cities ADD COLUMN IF NOT EXISTS geom GEOMETRY(Point, 4326);

-- 4. Populate Geometry from Lat/Lon
UPDATE cities 
SET geom = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
WHERE geom IS NULL AND lat IS NOT NULL AND lon IS NOT NULL;

-- 5. Create Spatial Index
CREATE INDEX IF NOT EXISTS idx_cities_geom ON cities USING GIST(geom);