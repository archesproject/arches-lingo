FROM public.ecr.aws/l1p7h1f9/archesproject-fargeo:7.6.x-base-dev
ENV WEB_ROOT=/web_root
ENV ARCHES_ROOT=${WEB_ROOT}/arches
ENV APP_ROOT=${WEB_ROOT}/arches-lingo
ENV NODE_MAJOR=20
ENV DEBIAN_FRONTEND=noninteractive

COPY ./arches ${ARCHES_ROOT}
RUN apt update && apt install wait-for-it openssh-client -y

COPY ../arches-lingo ${APP_ROOT}

WORKDIR ${APP_ROOT}
RUN source ../ENV/bin/activate && pip install -e '.[dev]' && pip uninstall arches -y

WORKDIR ${ARCHES_ROOT}
RUN source ../ENV/bin/activate && pip install -e . && pip install -e '.[dev]' --no-binary :all:

RUN mkdir /root/.ssh/

COPY /arches-lingo/docker/entrypoint.sh ${WEB_ROOT}/entrypoint.sh
RUN chmod -R 700 ${WEB_ROOT}/entrypoint.sh
WORKDIR ${WEB_ROOT}
ENTRYPOINT [ "./entrypoint.sh" ]
CMD ["run_webpack"]
EXPOSE 8021
