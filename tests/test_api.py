from fastapi.testclient import TestClient

from printready.api import app
from printready.models import DesignSpec

client = TestClient(app, base_url="http://localhost")


def test_generate_inspect_download():
    response = client.post("/api/jobs", json=DesignSpec(template="adapter").model_dump())
    assert response.status_code == 201
    job = response.json()
    assert client.get(f"/api/jobs/{job['id']}").json()["id"] == job["id"]
    assert client.get("/api/jobs").json()[0]["id"] == job["id"]
    download = client.get(job["artifacts"]["model.step"]["url"])
    assert download.status_code == 200 and b"ISO-10303-21" in download.content
    assert client.get(f"/api/jobs/{job['id']}/files/slicer-machine.json").status_code == 404
    assert client.get("/api/jobs/not-a-uuid").status_code == 404


def test_cross_origin_writes_rejected():
    assert (
        client.post("/api/jobs", json={}, headers={"Origin": "https://unrelated.example"}).status_code == 403
    )


def test_untrusted_host_is_rejected_before_local_operations():
    response = client.post("/api/jobs", json={}, headers={"Host": "unrelated.example"})
    assert response.status_code == 400


def test_no_physical_control_routes():
    assert client.get("/api/health").json()["physical_controls"] is False
    paths = app.openapi()["paths"]
    assert not any(word in path for path in paths for word in ("/print", "/heat", "/upload"))


def test_k1c_never_uses_a_bambu_profile():
    job = client.post("/api/jobs", json={"template": "adapter", "printer": "creality-k1c"}).json()
    result = client.post(f"/api/jobs/{job['id']}/slice", json={}).json()
    assert result["slicer"]["status"] != "completed"
