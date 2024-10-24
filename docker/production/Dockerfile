FROM public.ecr.aws/l1p7h1f9/archesproject-fargeo:7.6.x-base-prod AS base
ENV APP_ROOT=${WEB_ROOT}/arches-lingo
ENV ARCHES_DJANGO_DEBUG=True

WORKDIR ${WEB_ROOT}
RUN apt-get install nginx -y && ENV/bin/pip install gunicorn botocore boto3 django-storages psutil

COPY docker/nginx/default.conf /etc/nginx/sites-available/default

RUN  apt-get install wget -y && wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg \
  && apt-get install apt-transport-https \
  && echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | tee /etc/apt/sources.list.d/elastic-8.x.list \
  && apt-get update
RUN apt-get install sudo &&  echo 'Y' | adduser elasticsearch --disabled-password --ingroup "sudo" --gecos "First Last,RoomNumber,WorkPhone,HomePhone" && echo "elasticsearch ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers &&  su -c "sudo apt-get install elasticsearch" elasticsearch && exit 
RUN apt-get install postgresql-contrib-14 postgresql-14-postgis-3 -y && sed -i '1s/^/local all all trust\n/' /etc/postgresql/14/main/pg_hba.conf && (service postgresql start) \
  && echo "ALTER USER postgres WITH PASSWORD 'postgis';CREATE DATABASE template_postgis;CREATE EXTENSION postgis;\\q" | psql -Upostgres

RUN chown elasticsearch:elasticsearch /etc/elasticsearch -R && \
  chown elasticsearch:elasticsearch /usr/share/elasticsearch -R && \
  chown elasticsearch:elasticsearch /etc/default/elasticsearch 

RUN openssl ecparam -out /etc/ssl/private/nginx-selfsigned.key -name prime256v1 -genkey && openssl req -x509 -nodes -days 365 -newkey rsa:2048 -key /etc/ssl/private/nginx-selfsigned.key -out /etc/ssl/certs/nginx-selfsigned.crt -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=localhost"

COPY . ${WEB_ROOT}/arches-lingo
RUN source ${WEB_ROOT}/ENV/bin/activate && cd ${APP_ROOT} && pip install .

WORKDIR ${APP_ROOT}

RUN ESPASSWORD='$(echo "y" | sudo /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic | grep "New value:" | cut -d " " -f 3)' && export ES_JAVA_OPTS="-Xmx1g" && \
  sed -i 's/xpack.security.enabled: true/xpack.security.enabled: false/g' /etc/elasticsearch/elasticsearch.yml && \
  sed -i 's/xpack.security.enrollment.enabled: true/xpack.security.enrollment.enabled: false/g' /etc/elasticsearch/elasticsearch.yml && \
  (su -c "/usr/share/elasticsearch/bin/elasticsearch" elasticsearch>/dev/null 2>&1&) && \
  (service postgresql start) && sleep 30 && source ../ENV/bin/activate && (python3 manage.py setup_db --force) 

RUN source ../ENV/bin/activate && service postgresql start && \
  (/etc/init.d/nginx start&) && (gunicorn arches_lingo.wsgi&) && npm i && \
  npm run build_development && python3 manage.py collectstatic


FROM public.ecr.aws/l1p7h1f9/archesproject-fargeo:7.6.x-base-prod AS deploy 
USER root
ENV DEBIAN_FRONTEND=noninteractive
ENV WEB_ROOT=/web_root
ENV APP_ROOT=${WEB_ROOT}/arches-lingo
ENV BASE_WEB=/web_root
ENV BASE_APP=${BASE_WEB}/arches-lingo
COPY --from=base ${BASE_APP}/arches_lingo/staticfiles /var/www/media
COPY --from=base ${BASE_APP}/webpack/webpack-stats.json ${APP_ROOT}/webpack/webpack-stats.json
COPY --from=base /etc/ssl/private/nginx-selfsigned.key /etc/ssl/private/nginx-selfsigned.key
COPY --from=base /etc/ssl/certs/nginx-selfsigned.crt /etc/ssl/certs/nginx-selfsigned.crt

RUN chgrp www-data /var/www/media -R
RUN apt-get update && apt-get install -y make software-properties-common && apt-get install -y ca-certificates curl gnupg nginx vim && apt-add-repository ppa:deadsnakes/ppa && apt-get update

# Root project folder
ENV WHEELS=/wheels
ENV PYTHONUNBUFFERED=1

WORKDIR ${WEB_ROOT}

# Install the Arches application
# FIXME: ADD from github repository instead?

# From here, run commands from ARCHES_ROOT
RUN source ${WEB_ROOT}/ENV/bin/activate

COPY docker/production/entrypoint.sh ${WEB_ROOT}/entrypoint.sh
RUN chmod -R 700 ${WEB_ROOT}/entrypoint.sh &&\
  dos2unix ${WEB_ROOT}/entrypoint.sh

COPY . ${WEB_ROOT}/arches-lingo

# Set default workdir
WORKDIR ${APP_ROOT}
COPY docker/nginx/default.conf /etc/nginx/sites-available/default
RUN source ${WEB_ROOT}/ENV/bin/activate && pip install . && pip install gunicorn boto boto3 django-storages psutil

# # Set entrypoint
ENTRYPOINT ["../entrypoint.sh"]
CMD ["run_gunicorn"]

# Expose port 8000
EXPOSE 8000
