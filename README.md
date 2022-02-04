# wave2web-api
A basic API Flask app to serve wave2web inference.

The API is live at [https://h2ox-api.herokuapp.com/api/]. The API must be queried with a reservoir name, one of {harangi, hemavathy, kabini, krisharaja}, and the query date in YYYY-MM-DD format. See [demo.ipynb](demo.ipynb) or below for useage details.

A username and password are required. Please contact us for access!

**Useage (e.g. using Python's requests library):**

    import requests, json

    url = "https://h2ox-api.herokuapp.com/api/"

    r = requests.get(
        url = url,
        params = {"reservoir":"kabini", "date":"2014-03-03"},
        auth = ("<username>","<password>")
    )

    data = json.loads(r.text)

## Running the flask app
First load Google Cloud credentials from a Service Account JSON:
```
export GOOGLE_CREDENTIALS=$(cat credentials.json)
```
```
USERNAME=... USERPASSWORD=... FLASK_DEBUG=1 FLASK_APP=app.py flask run --port=5111
```
