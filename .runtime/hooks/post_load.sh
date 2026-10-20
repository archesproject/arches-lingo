#/bin/bash
/opt/ENV/bin/python manage.py load_lingo_fixtures --no-index

echo "VACUUM ANALYZE tiles;" | python manage.py dbshell
echo "VACUUM ANALYZE resource_instances;" | python manage.py dbshell
