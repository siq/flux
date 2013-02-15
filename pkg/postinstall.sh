#!/bin/sh
logreopen=${VARPATH}/flux.logreopen
if [ ! -e "$logreopen" ]; then
  touch $logreopen
fi

/siq/env/python/bin/python /siq/env/python/bin/bake -m spire.tasks \
  spire.schema.deploy schema=flux config=/siq/svc/flux/flux.yaml
ln -sf ${SVCPATH}/flux/flux.yaml ${CONFPATH}/uwsgi/flux.yaml
