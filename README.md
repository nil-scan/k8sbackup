# K8s Backup Controller

Automatically back up kubernetes resources to git

Any git ref can be restore by creating a RestoreJob CR

```yaml
apiVersion: k8sbackup.dev/v1
kind: RestoreJob
metadata:
  namespace: k8s-backup
  name: restore-stable
spec:
  gitRef: stable
```
