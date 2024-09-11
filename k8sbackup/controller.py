import kopf
import os
import yaml
import kubernetes
import logging

OUTPUT_DIR = os.environ.get('K8SBACKUP_OUTPUT_DIR', '_output')

@kopf.on.startup()
async def startup_fn(logger, settings: kopf.OperatorSettings, **_):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.system(f'git init {OUTPUT_DIR}')

    # Log errors as k8s events
    settings.posting.enabled = os.environ.get('EASYAAS_EVENT_ON_ERROR', '0') == 'true'
    settings.posting.level = int(os.environ.get('EASYAAS_LOG_LEVEL', logging.ERROR))

    # Initialize the k8s client
    try:
        kubernetes.config.load_incluster_config()
    except kubernetes.config.ConfigException:
        kubernetes.config.load_kube_config(config_file='~/.kube/config'
                                           , context='docker-desktop'
                                           )

@kopf.on.event('gateway.solo.io', kopf.EVERYTHING)
def backup_resources(namespace, name, body, **_):
    api_version = body['apiVersion']
    kind = body['kind']
    meta = dict(body['metadata'])
    spec = dict(body['spec'])

    meta.pop('managedFields')
    meta.pop('generation')
    meta.pop('resourceVersion')
    meta.pop('uid')

    path = f'{OUTPUT_DIR}/{namespace}/{kind}'
    os.makedirs(path, exist_ok=True)
    with open(f'{path}/{name}.yaml', 'w') as f:
        content = {
            'apiVersion': api_version,
            'kind': kind,
            'metadata': meta,
            'spec': spec,
        }
        f.write(yaml.dump(content))

    os.system(f'git -C {OUTPUT_DIR} add --all')
    os.system(f'git -C {OUTPUT_DIR} commit -m "Update to {namespace}/{name}"')

@kopf.on.create('k8sbackup.dev', 'restorejob')
def restore_resources(body, spec, **_):
    try:
        git_ref = spec['gitRef']
    except KeyError:
        kopf.event(body,
               type='RestoreError',
               reason='RefNotSpecified',
               message='Git ref not specified')
        
    try:
        os.system(f'git reset --hard {git_ref} --')
        os.system(f'kubectl apply --recursive -f {OUTPUT_DIR}')
    except Exception:
        kopf.event(body,
               type='RestoreError',
               reason='RefNotFound',
               message=f'Git ref {git_ref} not found')
