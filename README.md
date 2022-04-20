# wave2web-api
A basic FastAPI app to serve wave2web inference.

The [API is live here](https://api.h2ox.org/).

You can see the API's [OpenAPI documentation here](https://api.h2ox.org/docs).

A username and password are required. Please contact us for access!

### Local development
## Running the app directly
First load Google Cloud credentials from a Service Account JSON:
```bash
export GOOGLE_CREDENTIALS=$(cat credentials.json)
export REDIS_HOST=...
export REDIS_PORT=...
export REDIS_PW=...

USERNAME=... PASSWORD=... uvicorn app.app:app --port=5111 --reload
```

## Running with Docker
```bash
docker build -t h2ox-api .

docker run \
  -e GOOGLE_CREDENTIALS="$GOOGLE_CREDENTIALS" \
  -e REDIS_HOST="$REDIS_HOST" \
  -e REDIS_PORT="$REDIS_PORT" \
  -e REDIS_PW=$REDIS_PW \
  -e USERNAME=... \
  -e PASSWORD=... \
  -e PORT=5111 \
  -p 5111:5111 \
  h2ox-api
```

And then go to http://localhost:5111/ for the API and http://localhost:5111/docs to see the auto-generated docs.

## Putting into production on GCP
### Build on Cloud Build
```bash
gcloud builds submit . \
  --tag=eu.gcr.io/oxeo-main/h2ox-api \
  --ignore-file=.dockerignore
```

### Create a Cloud Run service
Based on the image created above, and make sure to provide all the same environment variables as provided above in the `docker run` command.
