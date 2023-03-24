# Trusted Profiles on IBM Cloud
Some tests of Trusted Profiles with Compute Resources on IBM Cloud.

The [app.py](app.py) creates two API functions:
- `localhost:8080/`: check that the app works and return the current app version
- `localhost:8080/api/listresources` with optional query parameter **tpname**: retrieve the service account token, turn it into an IBM Cloud IAM access token, retrieve the list of resources in the cloud account

To deploy, build the container image using the [Dockerfile](Dockerfile), then apply [app.yaml](app.yaml). Note that you need to change the container image specification in that file.

Once deployed, you can log into the running container:
```
kubectl exec --namespace default --stdin --tty tp-demo -- /bin/bash
```

Within the container shell use **curl** to access the API:
```
curl localhost:8080
```
or:
```
curl localhost:8080/api/listresources?tpname=TrustedProfile_Test
```