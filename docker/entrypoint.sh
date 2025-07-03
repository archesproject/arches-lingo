#!/bin/bash

# APP and npm folder locations
# ${WEB_ROOT} and ${ARCHES_ROOT} is defined in the Dockerfile, ${ARCHES_PROJECT} in env_file.env
if [[ -z ${ARCHES_PROJECT} ]]; then
	APP_FOLDER=${ARCHES_ROOT}
	PACKAGE_JSON_FOLDER=${ARCHES_ROOT}
else
	APP_FOLDER=${WEB_ROOT}/${ARCHES_PROJECT}
	PACKAGE_JSON_FOLDER=${ARCHES_ROOT}
fi

# Environmental Variables
export DJANGO_PORT=${DJANGO_PORT:-8000}

#Utility functions that check db status
wait_for_db() {
	echo "Testing if database server is up..."
	while [[ ! ${return_code} == 0 ]]
	do
        psql --host=${PGHOST} --port=${PGPORT} --user=${PGUSER} --dbname=postgres -c "select 1" >&/dev/null
		return_code=$?
		sleep 1
	done
	echo "Database server is up"

    echo "Testing if Elasticsearch is up..."
    while [[ ! ${return_code} == 0 ]]
    do
        curl -s "http://${ARCHES_ESHOST}:${ARCHES_ESPORT}/_cluster/health?wait_for_status=green&timeout=60s" >&/dev/nullB
        return_code=$?
        sleep 1
    done
    echo "Elasticsearch is up"
}

db_exists() {
	echo "Checking if database "${PGDBNAME}" exists..."
	count=`psql --host=${PGHOST} --port=${PGPORT} --user=${PGUSER} --dbname=postgres -Atc "SELECT COUNT(*) FROM pg_catalog.pg_database WHERE datname='${PGDBNAME}'"`

	# Check if returned value is a number and not some error message
	re='^[0-9]+$'
	if ! [[ ${count} =~ $re ]] ; then
	   echo "Error: Something went wrong when checking if database "${PGDBNAME}" exists..." >&2;
	   echo "Exiting..."
	   exit 1
	fi

	# Return 0 (= true) if database exists
	if [[ ${count} > 0 ]]; then
		return 0
	else
		return 1
	fi
}

#### Install
init_arches() {
	echo "Checking if Arches project "${ARCHES_PROJECT}" exists..."
	if [[ ! -d ${APP_FOLDER} ]] || [[ ! "$(ls ${APP_FOLDER})" ]]; then
		echo ""
		echo "----- Custom Arches project '${ARCHES_PROJECT}' does not exist. -----"
		echo "----- Creating '${ARCHES_PROJECT}'... -----"
		echo ""

		cd ${WEB_ROOT}

		arches-project create ${ARCHES_PROJECT}
		run_setup_db

		exit_code=$?
		if [[ ${exit_code} != 0 ]]; then
			echo "Something went wrong when creating your Arches project: ${ARCHES_PROJECT}."
			echo "Exiting..."
			exit ${exit_code}
		fi
	else
		echo "Custom Arches project '${ARCHES_PROJECT}' exists."
		wait_for_db
		if db_exists; then
			echo "Database ${PGDBNAME} already exists."
			echo "Skipping Package Loading"
		else
			echo "Database ${PGDBNAME} does not exists yet."
			run_load_package #change to run_load_package if preferred 
		fi
	fi
}

#### Run commands

start_celery_supervisor() {
	cd ${APP_FOLDER}
	supervisord -c docker/arches-supervisor.conf
}

run_migrations() {
	echo ""
	echo "----- RUNNING DATABASE MIGRATIONS -----"
	echo ""
	cd ${APP_FOLDER}
	python3 manage.py migrate
}

run_setup_db() {
	echo ""
	echo "----- RUNNING SETUP_DB -----"
	echo ""
	cd ${APP_FOLDER}
	python3 manage.py setup_db --force
}

run_load_package() {
	echo ""
	echo "----- *** LOADING PACKAGE: ${ARCHES_PROJECT} *** -----"
	echo ""
	cd ${APP_FOLDER}
	python3 manage.py packages -o load_package -a arches_lingo -db -dev -y
}

# "exec" means that it will finish building???
run_django_server() {
	echo ""
	echo "----- *** RUNNING DJANGO DEVELOPMENT SERVER *** -----"
	echo ""
	cd ${APP_FOLDER}
    echo "Running Django"
	exec /bin/bash -c "source ${WEB_ROOT}/ENV/bin/activate && gunicorn arches_lingo.wsgi"
}

run_dev_server() {
	echo ""
	echo "----- *** RUNNING DJANGO DEVELOPMENT SERVER *** -----"
	echo ""
	cd ${APP_FOLDER}
    echo "Running Django"
	exec /bin/bash -c "source ../ENV/bin/activate && cd ../arches-component-lab/ && pip install -e . && cd ../arches-controlled-lists && pip install -e . && cd ../arches && pip install -e . && cd ../arches-lingo && pip3 install debugpy -t /tmp && python -Wdefault /tmp/debugpy --listen 0.0.0.0:5678 manage.py runserver 0.0.0.0:${DJANGO_PORT}"
}

# "exec" means that it will finish building???
run_gunicorn() {
	echo ""
	echo "----- *** RUNNING DJANGO PRODUCTION SERVER *** -----"
	echo ""
	cd ${APP_ROOT}
    echo "Running Django"
	service memcached start&
	exec /bin/bash -c "source ../ENV/bin/activate && (/etc/init.d/nginx start&) && gunicorn --workers=$(($(nproc --all)+1)) arches_lingo.wsgi"
}


reset_database() {
	echo ""
	echo "----- RESETTING DATABASE -----"
	echo ""
	cd ${APP_ROOT}
	pwd && ../ENV/bin/python --version
	(test $(echo "SELECT FROM pg_database WHERE datname = 'template_postgis'" | ../ENV/bin/python manage.py dbshell | grep -c "1 row") = 1 || \
	(echo "CREATE DATABASE template_postgis" | ../ENV/bin/python manage.py dbshell --database postgres && \
	echo "CREATE EXTENSION postgis" | ../ENV/bin/python manage.py dbshell --database postgres))
	service memcached start&
	../ENV/bin/python manage.py packages -o load_package -a arches_lingo -db -dev -y
	../ENV/bin/python manage.py loaddata tests/fixtures/data/FISH_Thesauri_example_data_resources.json tests/fixtures/data/FISH_Thesauri_example_data_tiles.json
	../ENV/bin/python manage.py es reindex_database -mp
}

activate_virtualenv() {
	. ${WEB_ROOT}/ENV/bin/activate
}

#### Main commands
run_arches() {
	run_django_server
}

### Starting point ###

# Use -gt 1 to consume two arguments per pass in the loop
# (e.g. each argument has a corresponding value to go with it).
# Use -gt 0 to consume one or more arguments per pass in the loop
# (e.g. some arguments don't have a corresponding value to go with it, such as --help ).

# If no arguments are supplied, assume the server needs to be run
if [[ $#  -eq 0 ]]; then
	start_celery_supervisor
	wait_for_db
	run_arches
fi

# Else, process arguments
echo "Full command: $@"
while [[ $# -gt 0 ]]
do
	key="$1"
	echo "Command: ${key}"

	case ${key} in
		run_arches)
			start_celery_supervisor
			wait_for_db
			run_arches
		;;
		setup_arches)
			start_celery_supervisor
			wait_for_db
			setup_arches
		;;
		run_tests)
			wait_for_db
			run_tests
		;;
		run_migrations)
			wait_for_db
			run_migrations
		;;

		help|-h)
			display_help
		;;
		*)
            cd ${APP_FOLDER}
			"$@"
			exit 0
		;;
	esac
	shift # next argument or value
done
