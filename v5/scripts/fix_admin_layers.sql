-- 1. Add Geometry Column to Countries (if missing)
ALTER TABLE countries 
ADD COLUMN IF NOT EXISTS geom GEOMETRY(MultiPolygon, 4326);

-- 2. Index Countries
CREATE INDEX IF NOT EXISTS idx_countries_geom ON countries USING GIST(geom);

-- 3. Add Geometry Column to States (if missing)
ALTER TABLE states 
ADD COLUMN IF NOT EXISTS geom GEOMETRY(MultiPolygon, 4326);

-- 4. Index States
CREATE INDEX IF NOT EXISTS idx_states_geom ON states USING GIST(geom);

-- 5. Verification (Optional)
SELECT 'Countries' as table_name, count(*) as cols FROM information_schema.columns WHERE table_name='countries' AND column_name='geom'
UNION ALL
SELECT 'States' as table_name, count(*) as cols FROM information_schema.columns WHERE table_name='states' AND column_name='geom';