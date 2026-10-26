# Geoapify configuration

The backend reads `GEOAPIFY_KEY` from its environment when the location
repository is created. It uses this key for location autocomplete and place
details requests.

For k3s, set `data.GEOAPIFY_KEY` in `k8s/02-secrets.yaml` to the base64-encoded
key. The Secret must be named `makeascene-secrets` in namespace `makeascene`.
The backend Deployment imports every key from this Secret through `envFrom`;
Kubernetes decodes the value before passing it to the container. No application
decoding or additional environment mapping is needed.

After changing the Secret, apply it and restart the backend. Existing pods keep
their previous environment until they are replaced:

```sh
kubectl apply -f k8s/02-secrets.yaml
kubectl rollout restart deployment/backend -n makeascene
kubectl rollout status deployment/backend -n makeascene
```

For Docker Compose, put the raw, unencoded key in `secrets.env`:

```dotenv
GEOAPIFY_KEY=your-actual-key
```

Compose loads this file into the backend through `env_file`. Recreate the
container after changing it:

```sh
docker compose up -d --no-deps --force-recreate backend
```

Verify presence in a running container without printing the key:

```sh
kubectl exec -n makeascene deployment/backend -- sh -c 'test -n "$GEOAPIFY_KEY" && echo GEOAPIFY_KEY-is-set'
docker compose exec backend sh -c 'test -n "$GEOAPIFY_KEY" && echo GEOAPIFY_KEY-is-set'
```
