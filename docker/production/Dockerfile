FROM public.ecr.aws/l1p7h1f9/archesproject-fargeo:8.0.x-base-prod AS base
ENV APP_ROOT=${WEB_ROOT}/arches-lingo
ENV ARCHES_DJANGO_DEBUG=True

WORKDIR ${WEB_ROOT}
RUN apt-get install nginx -y && ENV/bin/pip install gunicorn botocore boto3 django-storages psutil

RUN openssl ecparam -out /etc/ssl/private/nginx-selfsigned.key -name prime256v1 -genkey && openssl req -x509 -nodes -days 365 -newkey rsa:2048 -key /etc/ssl/private/nginx-selfsigned.key -out /etc/ssl/certs/nginx-selfsigned.crt -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=localhost"

COPY . ${WEB_ROOT}/arches-lingo
RUN source ${WEB_ROOT}/ENV/bin/activate && cd ${APP_ROOT} && pip install .
COPY ./docker/static_frontend_configuration ${WEB_ROOT}/arches-lingo/frontend_configuration
WORKDIR ${APP_ROOT}
RUN npm i
RUN source ../ENV/bin/activate && npm run build_production_unsafe && python3 manage.py collectstatic


FROM public.ecr.aws/l1p7h1f9/archesproject-fargeo:8.0.x-base-prod AS deploy 
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

#TODO: remove memcached from this image
RUN apt-get update && apt-get install -y make software-properties-common memcached && apt-get install -y ca-certificates curl gnupg nginx vim && apt-add-repository ppa:deadsnakes/ppa && apt-get update

# Root project folder
ENV WHEELS=/wheels
ENV PYTHONUNBUFFERED=1

WORKDIR ${WEB_ROOT}

# Install the Arches application
# FIXME: ADD from github repository instead?

# From here, run commands from ARCHES_ROOT
RUN source ${WEB_ROOT}/ENV/bin/activate

COPY docker/entrypoint.sh ${WEB_ROOT}/entrypoint.sh
RUN chmod -R 700 ${WEB_ROOT}/entrypoint.sh &&\
  dos2unix ${WEB_ROOT}/entrypoint.sh

COPY . ${WEB_ROOT}/arches-lingo

# Set default workdir
WORKDIR ${APP_ROOT}
COPY docker/nginx/default.conf /etc/nginx/sites-available/default

#TODO: remove pymemcacheD from this image
RUN source ${WEB_ROOT}/ENV/bin/activate && pip install . && pip install gunicorn pymemcache boto boto3 django-storages psutil

# # Set entrypoint
ENTRYPOINT ["../entrypoint.sh"]
CMD ["run_gunicorn"]

# Expose port 8000
EXPOSE 8000
