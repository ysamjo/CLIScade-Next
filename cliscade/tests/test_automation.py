import io
import json
import tarfile
from types import SimpleNamespace

import httpx

from cliscade_next.automation import Automation
from cliscade_next.scheduled import dispatch


def test_native_automation_upload_has_no_credentials_and_uses_cron_contract():
    requests = []

    def handle(request):
        requests.append(request)
        if request.url.path.endswith("/uploads"):
            with tarfile.open(fileobj=io.BytesIO(request.content), mode="r:gz") as tar:
                config = json.load(tar.extractfile("cliscade.json"))
                assert "api_key" not in config
                assert config["task_id"] == "cn-1"
            return httpx.Response(201, json={"tarball_path": "oh-internal://upload"})
        body = json.loads(request.content)
        assert body["trigger"] == {
            "type": "cron",
            "schedule": "0 9 * * 1",
            "timezone": "Europe/Berlin",
        }
        assert body["timeout"] <= 1800
        assert (
            body["entrypoint"]
            == "uv run --script --locked cliscade-dispatch.py cliscade.json"
        )
        return httpx.Response(201, json={"id": "automation"})

    result = Automation(
        SimpleNamespace(api_key="test-key"), httpx.MockTransport(handle)
    ).create("project", "cn-1", "auto", "0 9 * * 1", "Europe/Berlin")
    assert result["id"] == "automation"
    assert len(requests) == 2


def test_scheduled_dispatch_uses_stable_run_key_and_waits_for_completion():
    def handle(request):
        if request.method == "POST":
            assert json.loads(request.content)["request_key"] == "automation:run-1"
            return httpx.Response(201, json={"id": "a1", "status": "running"})
        if request.url.path.endswith("/cn-1"):
            return httpx.Response(200, json={"id": "cn-1", "status": "open"})
        return httpx.Response(200, json={"id": "a1", "status": "completed"})

    with httpx.Client(
        base_url="http://cliscade", transport=httpx.MockTransport(handle)
    ) as client:
        result = dispatch(
            {"project": "project", "task_id": "cn-1", "agent_id": "auto"},
            client,
            "run-1",
            poll_seconds=0,
        )
    assert result["status"] == "completed"


def test_scheduled_run_carries_the_model_into_the_attempt():
    payloads = []

    def handle(request):
        if request.method == "POST":
            payloads.append(json.loads(request.content))
            return httpx.Response(201, json={"id": "a1", "status": "running"})
        if request.url.path.endswith("/cn-1"):
            return httpx.Response(200, json={"id": "cn-1", "status": "open"})
        return httpx.Response(200, json={"id": "a1", "status": "completed"})

    with httpx.Client(
        base_url="http://cliscade", transport=httpx.MockTransport(handle)
    ) as client:
        dispatch(
            {
                "project": "project",
                "task_id": "cn-1",
                "agent_id": "auto",
                "model": "openai/c1",
            },
            client,
            "run-2",
            poll_seconds=0,
        )
    assert payloads[0]["model"] == "openai/c1"


def test_schedule_without_model_does_not_send_one():
    payloads = []

    def handle(request):
        if request.method == "POST":
            payloads.append(json.loads(request.content))
            return httpx.Response(201, json={"id": "a1", "status": "running"})
        if request.url.path.endswith("/cn-1"):
            return httpx.Response(200, json={"id": "cn-1", "status": "open"})
        return httpx.Response(200, json={"id": "a1", "status": "completed"})

    with httpx.Client(
        base_url="http://cliscade", transport=httpx.MockTransport(handle)
    ) as client:
        dispatch(
            {"project": "project", "task_id": "cn-1", "agent_id": "auto"},
            client,
            "run-3",
            poll_seconds=0,
        )
    assert "model" not in payloads[0]


def test_automation_bundle_carries_the_model_and_changes_identity():
    configs = []

    def handle(request):
        if request.url.path.endswith("/uploads"):
            with tarfile.open(fileobj=io.BytesIO(request.content), mode="r:gz") as tar:
                configs.append(json.load(tar.extractfile("cliscade.json")))
            return httpx.Response(201, json={"tarball_path": "oh-internal://upload"})
        return httpx.Response(201, json={"id": "automation"})

    create = Automation(
        SimpleNamespace(api_key="test-key"), httpx.MockTransport(handle)
    ).create
    create("project", "cn-1", "auto", "0 9 * * 1", "Europe/Berlin", model="openai/c1")
    create("project", "cn-1", "auto", "0 9 * * 1", "Europe/Berlin")
    assert configs[0]["model"] == "openai/c1"
    assert "model" not in configs[1]
