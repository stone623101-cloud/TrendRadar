import gzip
import hashlib
import http.client
import json
import os
import sys


def _patch(token: str, path: str, body: dict) -> dict:
    conn = http.client.HTTPSConnection("firebasehosting.googleapis.com")
    conn.request(
        "PATCH",
        f"{path}?updateMask=status",
        body=json.dumps(body),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    resp = conn.getresponse()
    data = resp.read()
    result = json.loads(data)
    if resp.status >= 400:
        raise RuntimeError(f"HTTP {resp.status} PATCH {path}: {result}")
    return result


def _post(token: str, host: str, path: str, body: bytes, extra_headers: dict = None) -> dict:
    conn = http.client.HTTPSConnection(host)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    conn.request("POST", path, body=body, headers=headers)
    resp = conn.getresponse()
    data = resp.read()
    result = json.loads(data) if data else {}
    if resp.status >= 400:
        raise RuntimeError(f"HTTP {resp.status} {path}: {result}")
    return result


def upload():
    html_path = "/app/output/index.html"
    site_id = os.environ.get("FIREBASE_SITE_ID", "news-sparkstudio")

    if not os.path.exists(html_path):
        print(f"[upload] {html_path} not found, skipping")
        sys.exit(0)

    try:
        import google.auth
        import google.auth.transport.requests

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/firebase"]
        )
        credentials.refresh(google.auth.transport.requests.Request())
        token = credentials.token

        with open(html_path, "rb") as f:
            raw = f.read()
        gz = gzip.compress(raw)
        sha256 = hashlib.sha256(gz).hexdigest()

        base = f"/v1beta1/sites/{site_id}"

        # 1. Create version
        version = _post(token, "firebasehosting.googleapis.com", f"{base}/versions",
                        json.dumps({"config": {"headers": [{"glob": "**", "headers": {"Cache-Control": "max-age=1800"}}]}}).encode())
        version_name = version["name"]
        print(f"[upload] version: {version_name.split('/')[-1]}")

        # 2. Declare files
        populate = _post(token, "firebasehosting.googleapis.com",
                         f"/v1beta1/{version_name}:populateFiles",
                         json.dumps({"files": {"/index.html": sha256}}).encode())
        upload_url = populate.get("uploadUrl", "")
        needs_upload = sha256 in populate.get("uploadRequiredHashes", [])

        # 3. Upload if needed
        if needs_upload and upload_url:
            from urllib.parse import urlparse
            u = urlparse(upload_url)
            conn = http.client.HTTPSConnection(u.netloc)
            conn.request("POST", f"{u.path}/{sha256}",
                         body=gz,
                         headers={
                             "Authorization": f"Bearer {token}",
                             "Content-Type": "application/octet-stream",
                             "Content-Length": str(len(gz)),
                         })
            up_resp = conn.getresponse()
            up_resp.read()
            if up_resp.status >= 400:
                raise RuntimeError(f"Upload failed HTTP {up_resp.status}")
            print(f"[upload] uploaded index.html ({len(gz):,} bytes gzipped)")
        else:
            print("[upload] file unchanged, using cache")

        # 4. Finalize
        _patch(token, f"/v1beta1/{version_name}", {"status": "FINALIZED"})
        print("[upload] finalized")

        # 5. Release (version_name has slashes, must be URL-encoded in query)
        from urllib.parse import quote
        encoded = quote(version_name, safe="")
        _post(token, "firebasehosting.googleapis.com",
              f"{base}/releases?versionName={encoded}",
              b"{}")
        print(f"[upload] live → https://{site_id}.web.app")

    except Exception as e:
        print(f"[upload] failed: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)


def upload_to_gcs():
    html_path = "/app/output/index.html"
    bucket_name = os.environ.get("GCS_BUCKET", "news.sparkstudio.info")

    if not os.path.exists(html_path):
        print(f"[gcs] {html_path} not found, skipping")
        return

    try:
        from google.cloud import storage as gcs_storage
        client = gcs_storage.Client()
        blob = client.bucket(bucket_name).blob("index.html")
        blob.upload_from_filename(html_path, content_type="text/html; charset=utf-8")
        blob.cache_control = "max-age=1800, public"
        blob.patch()
        print(f"[gcs] uploaded → gs://{bucket_name}/index.html")
    except Exception as e:
        print(f"[gcs] upload failed: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    upload()
    upload_to_gcs()
