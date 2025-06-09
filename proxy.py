from flask import Flask, request, Response, abort
import os
import mimetypes
import requests
from urllib.parse import urljoin

app = Flask(__name__)

CACHE_DIR = "cache"
REMOTE_BASE_URL = "https://stellarium.sfo2.cdn.digitaloceanspaces.com"

# Utility: crea struttura cache
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_path(path):
    return os.path.join(CACHE_DIR, path.strip("/"))

# Aggiungi CORS manualmente a ogni risposta
def cors_response(data, mimetype="application/octet-stream", status=200):
    return Response(
        data,
        status=status,
        mimetype=mimetype,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.route('/', defaults={'req_path': ''}, methods=["GET", "OPTIONS"])
@app.route('/<path:req_path>', methods=["GET", "OPTIONS"])
def proxy(req_path):
    # Gestione preflight CORS
    if request.method == "OPTIONS":
        return cors_response(b'', status=204)

    local_path = get_cache_path(req_path)
    remote_url = urljoin(REMOTE_BASE_URL + "/", req_path)

    # Se è in cache → serve
    if os.path.isfile(local_path):
        return serve_file(local_path)

    # Altrimenti scarica
    try:
        print(f"Scarico da: {remote_url}")
        response = requests.get(remote_url, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        return serve_file(local_path)

    except requests.HTTPError as e:
        print(f"Errore HTTP: {e}")
        return cors_response(str(e).encode(), status=response.status_code)
    except Exception as e:
        print(f"Errore generico: {e}")
        return cors_response(str(e).encode(), status=500)

def serve_file(path):
    mimetype, _ = mimetypes.guess_type(path)
    with open(path, 'rb') as f:
        data = f.read()
    return cors_response(data, mimetype=mimetype or 'application/octet-stream')

if __name__ == '__main__':
    # Certificati mkcert
    app.run(
        host="0.0.0.0",
        port=443,
        ssl_context=("fakedomain.com.pem", "fakedomain.com-key.pem")
    )
