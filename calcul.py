import os

from configparser import ConfigParser
from urllib.request import urlretrieve

config = ConfigParser()
config.read('env.cfg')

DB_NAME = config.get('POSTGRES', 'DB_NAME')
DB_HOST = config.get('POSTGRES', 'DB_HOST')
DB_PORT = config.get('POSTGRES', 'DB_PORT')
DB_USER = config.get('POSTGRES', 'DB_USER')
DB_PASSWORD = config.get('POSTGRES', 'DB_PASSWORD')

postgres_connection_str_ogr2ogr = f"dbname='{DB_NAME}' host='{DB_HOST}' port='{DB_PORT}' user='{DB_USER}' password='{DB_PASSWORD}'"
postgres_connection_str_psql = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

SOURCE = config.get('OCSGE', 'OCSGE_OCCUPATION_DU_SOL_7Z_URL')
DESTINATION = config.get('DIRECTORIES', 'DOWNLOAD_DESTINATION')
EXTRACT_DESTINATION = config.get('DIRECTORIES', 'EXTRACT_DESTINATION')

occupation_du_sol_shapefile_path = f"{EXTRACT_DESTINATION}/{config.get('OCSGE', 'OCCUPATION_DU_SOL_SHAPEFILE_NAME')}"

urlretrieve(url=SOURCE, filename=DESTINATION)

os.system(command=f'7z e -y {DESTINATION} -o{EXTRACT_DESTINATION}')
os.system(command=f'psql -d {postgres_connection_str_psql} -c "CREATE EXTENSION IF NOT EXISTS postgis;"')
os.system(command=f"ogr2ogr -lco OVERWRITE=YES -lco GEOMETRY_NAME=mpoly -f PostgreSQL PG:\"{postgres_connection_str_ogr2ogr}\" {occupation_du_sol_shapefile_path} --config PG_USE_COPY YES -nln occupation_sol -nlt PROMOTE_TO_MULTI")

sql_command = '''
DROP TABLE IF EXISTS surface_artificialisee;
CREATE TABLE surface_artificialisee AS
WITH ocsge_classified AS ( /* assign is_artificial value to each object */
    SELECT
    *,
    CASE
        /* CS 1.1 */
        WHEN code_cs = 'CS1.1.1.1' THEN TRUE
        WHEN code_cs = 'CS1.1.1.2' THEN TRUE
        WHEN code_cs = 'CS1.1.1.1' AND code_us != 'US1.3' THEN TRUE
        WHEN code_cs = 'CS1.1.2.1' THEN TRUE
        WHEN code_cs = 'CS1.1.2.2' THEN TRUE
    
        /* CS 2.2 */
            /* CS 2.2.1 */
            WHEN code_cs = 'CS2.2.1' AND code_us = 'US2' THEN TRUE
            WHEN code_cs = 'CS2.2.1' AND code_us = 'US3' THEN TRUE
            WHEN code_cs = 'CS2.2.1' AND code_us = 'US5' THEN TRUE
            WHEN code_cs = 'CS2.2.1' AND code_us = 'US235' THEN TRUE
            WHEN code_cs = 'CS2.2.1' AND code_us = 'US4.1.1' THEN TRUE
            WHEN code_cs = 'CS2.2.1' AND code_us = 'US4.1.2' THEN TRUE
            WHEN code_cs = 'CS2.2.1' AND code_us = 'US4.1.3' THEN TRUE
            WHEN code_cs = 'CS2.2.1' AND code_us = 'US4.1.4' THEN TRUE
            WHEN code_cs = 'CS2.2.1' AND code_us = 'US4.1.5' THEN TRUE
            WHEN code_cs = 'CS2.2.1' AND code_us = 'US4.2' THEN TRUE
            WHEN code_cs = 'CS2.2.1' AND code_us = 'US4.3' THEN TRUE
            WHEN code_cs = 'CS2.2.1' AND code_us = 'US6.1' THEN TRUE
            WHEN code_cs = 'CS2.2.1' AND code_us = 'US6.2' THEN TRUE

            /* CS 2.2.2 */
            WHEN code_cs = 'CS2.2.2' AND code_us = 'US2' THEN TRUE
            WHEN code_cs = 'CS2.2.2' AND code_us = 'US3' THEN TRUE
            WHEN code_cs = 'CS2.2.2' AND code_us = 'US5' THEN TRUE
            WHEN code_cs = 'CS2.2.2' AND code_us = 'US235' THEN TRUE
            WHEN code_cs = 'CS2.2.2' AND code_us = 'US4.1.1' THEN TRUE
            WHEN code_cs = 'CS2.2.2' AND code_us = 'US4.1.2' THEN TRUE
            WHEN code_cs = 'CS2.2.2' AND code_us = 'US4.1.3' THEN TRUE
            WHEN code_cs = 'CS2.2.2' AND code_us = 'US4.1.4' THEN TRUE
            WHEN code_cs = 'CS2.2.2' AND code_us = 'US4.1.5' THEN TRUE
            WHEN code_cs = 'CS2.2.2' AND code_us = 'US4.2' THEN TRUE
            WHEN code_cs = 'CS2.2.2' AND code_us = 'US4.3' THEN TRUE
            WHEN code_cs = 'CS2.2.2' AND code_us = 'US6.1' THEN TRUE
            WHEN code_cs = 'CS2.2.2' AND code_us = 'US6.2' THEN TRUE
        ELSE FALSE
    END AS is_artificial
    FROM
    occupation_sol
),
clustered_ocsge AS ( /* group artificial and non_artficial objects by their proximity  */
    SELECT
        is_artificial,
        ST_UnaryUnion(
            unnest(
                ST_ClusterIntersecting(mpoly)
            )
        ) AS mpoly
    FROM
        ocsge_classified
    GROUP BY
        is_artificial
),
artif_nat_by_surface AS ( /* invert is_articicial value if the surface is inferior to 2500m2 */
    SELECT
        CASE
            WHEN ST_Area(mpoly) < 2500 THEN NOT is_artificial
            ELSE is_artificial
        END AS is_artificial,
        mpoly
    FROM
        clustered_ocsge
),
small_built AS ( /* retrieve small built surfaces that are enclaved in natural surfaces */
    SELECT
        is_artificial,
        mpoly
    FROM
        ocsge_classified
    WHERE
        code_cs = 'CS1.1.1.1'
        AND ST_Area(mpoly) < 2500
        AND EXISTS (
			SELECT
				mpoly
			FROM
				artif_nat_by_surface
			WHERE
				ST_Intersects(mpoly, ocsge_classified.mpoly) AND
				is_artificial = false
        ) 
), artificial_union AS (
    SELECT
        is_artificial,
        mpoly
    FROM
        artif_nat_by_surface
    WHERE
        is_artificial = true
    UNION ALL
    SELECT
        is_artificial,
        mpoly
    FROM
        small_built
), artificial_geom_union AS (
    SELECT
        ST_Union(mpoly) AS mpoly,
        is_artificial
    FROM
        artificial_union
    GROUP BY
        is_artificial
)
SELECT * FROM occupation_sol
WHERE
    ST_Intersects(
        ST_PointOnSurface(mpoly),
        (SELECT mpoly FROM artificial_geom_union)
    );
CREATE INDEX
    surface_artificialisee_idx
ON
    surface_artificialisee
USING gist (mpoly);
'''

os.system(command=f'psql -d {postgres_connection_str_psql} -c "{sql_command}"')