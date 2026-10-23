#/bin/bash
/opt/ENV/bin/python manage.py load_lingo_fixtures --no-index

# TEMPORARY - remove after 1.2.x release
echo "CREATE INDEX CONCURRENTLY IF NOT EXISTS tiles_uri_content_btree ON tiles ((tiledata -> 'bf73e64a-4888-11ee-8a8d-11afefc4bff7')) WHERE nodegroupid = 'bf73e598-4888-11ee-8a8d-11afefc4bff7';" | python manage.py dbshell
echo "CREATE INDEX CONCURRENTLY IF NOT EXISTS tiles_part_of_scheme_covering ON tiles (resourceinstanceid) INCLUDE (tiledata, parenttileid, sortorder) WHERE nodegroupid = 'bf73e60a-4888-11ee-8a8d-11afefc4bff7';" | python manage.py dbshell
echo "CREATE INDEX CONCURRENTLY IF NOT EXISTS tiles_part_of_scheme_gin ON tiles USING GIN ((tiledata -> 'bf73e60a-4888-11ee-8a8d-11afefc4bff7') jsonb_path_ops) WHERE nodegroupid = 'bf73e60a-4888-11ee-8a8d-11afefc4bff7';" | python manage.py dbshell
echo "VACUUM ANALYZE tiles;" | python manage.py dbshell
echo "VACUUM ANALYZE resource_instances;" | python manage.py dbshell