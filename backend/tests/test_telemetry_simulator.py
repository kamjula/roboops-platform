from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timezone

import httpx
import pytest

from scripts.telemetry_simulator import (
    HttpTelemetryTransport,
    SimulatorConfigError,
    TelemetryGenerator,
    TelemetrySimulator,
    build_parser,
    parse_sensor_configuration,
)

SENSOR_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
ROBOT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
TIMESTAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)


def sensor_entry(sensor_type="battery", unit="percent"):
    return {
        "sensor_id": str(SENSOR_ID),
        "robot_id": str(ROBOT_ID),
        "robot_code": "RBT-001",
        "sensor_type": sensor_type,
        "unit": unit,
    }


def sensor_config(sensor_type="battery", unit="percent"):
    return parse_sensor_configuration(json.dumps([sensor_entry(sensor_type, unit)]))[0]


def test_configuration_validation_rejects_duplicates_types_and_units():
    entry = sensor_entry()
    assert parse_sensor_configuration(json.dumps([entry]))[0].sensor_id == SENSOR_ID
    with pytest.raises(SimulatorConfigError, match="duplicate"):
        parse_sensor_configuration(json.dumps([entry, entry]))
    with pytest.raises(SimulatorConfigError, match="unsupported"):
        parse_sensor_configuration(json.dumps([sensor_entry("vibration", "percent")]))
    with pytest.raises(SimulatorConfigError, match="celsius"):
        parse_sensor_configuration(json.dumps([sensor_entry("temperature", "percent")]))


def test_generator_is_deterministic_bounded_and_gradual():
    sensors = (sensor_config(),)
    first = TelemetryGenerator(sensors, random.Random(7), run_id="run")
    second = TelemetryGenerator(sensors, random.Random(7), run_id="run")
    statuses = {ROBOT_ID: "active"}
    values_one = [first.generate_cycle(statuses, cycle, TIMESTAMP)[0].value for cycle in range(1, 5)]
    values_two = [second.generate_cycle(statuses, cycle, TIMESTAMP)[0].value for cycle in range(1, 5)]
    assert values_one == values_two
    assert all(0 <= value <= 100 for value in values_one)
    assert all(abs(values_one[index] - values_one[index - 1]) < 2 for index in range(1, len(values_one)))


def test_active_battery_drains_faster_than_idle():
    active = TelemetryGenerator((sensor_config(),), random.Random(1), run_id="active")
    idle = TelemetryGenerator((sensor_config(),), random.Random(1), run_id="idle")
    active_start = active.states[SENSOR_ID].value
    idle_start = idle.states[SENSOR_ID].value
    active_value = active.generate_cycle({ROBOT_ID: "active"}, 1, TIMESTAMP)[0].value
    idle_value = idle.generate_cycle({ROBOT_ID: "idle"}, 1, TIMESTAMP)[0].value
    assert active_start - active_value > idle_start - idle_value


def test_temperature_is_bounded_and_status_changes_target():
    generator = TelemetryGenerator((sensor_config("temperature", "celsius"),), random.Random(3), run_id="run")
    active = generator.generate_cycle({ROBOT_ID: "active"}, 1, TIMESTAMP)[0]
    idle = generator.generate_cycle({ROBOT_ID: "idle"}, 2, TIMESTAMP)[0]
    assert 10 <= active.value <= 60
    assert 10 <= idle.value <= 60
    assert active.source_event_id != idle.source_event_id


def test_offline_and_decommissioned_robots_emit_nothing_and_stay_disabled():
    generator = TelemetryGenerator((sensor_config(),), random.Random(1), run_id="run")
    assert generator.generate_cycle({ROBOT_ID: "offline"}, 1, TIMESTAMP) == []
    assert generator.generate_cycle({ROBOT_ID: "decommissioned"}, 2, TIMESTAMP) == []
    assert generator.generate_cycle({ROBOT_ID: "active"}, 3, TIMESTAMP) == []
    assert ROBOT_ID in generator.disabled_robots


class FakeTransport:
    def __init__(self, result=None):
        self.result = result
        self.events = []
        self.cycles = 0

    def robot_statuses(self):
        self.cycles += 1
        return {ROBOT_ID: "active"}

    def send(self, event):
        self.events.append(event)
        return self.result or type("Result", (), {"status_code": 201, "disable_sensor": False, "disable_robot": False})()


def test_simulator_cycles_and_payload_excludes_robot_id():
    transport = FakeTransport()
    sleeps = []
    simulator = TelemetrySimulator(
        TelemetryGenerator((sensor_config(),), random.Random(4), run_id="run"),
        transport,
        sleep=sleeps.append,
        clock=lambda: TIMESTAMP,
    )
    simulator.run(3, 10)
    assert transport.cycles == 3
    assert len(transport.events) == 3
    assert sleeps == [10, 10]
    assert "robot_id" not in transport.events[0].payload()
    assert len({event.source_event_id for event in transport.events}) == 3


def test_decommissioned_result_disables_remaining_robot_events():
    second_sensor = dict(sensor_entry(), sensor_id="33333333-3333-3333-3333-333333333333")
    sensors = parse_sensor_configuration(json.dumps([sensor_entry(), second_sensor]))
    result = type("Result", (), {"status_code": 409, "disable_sensor": False, "disable_robot": True})()
    transport = FakeTransport(result)
    simulator = TelemetrySimulator(TelemetryGenerator(sensors, random.Random(4), run_id="run"), transport, clock=lambda: TIMESTAMP)
    simulator.run(1, 0)
    assert len(transport.events) == 1


def test_cli_modes_validate_cycles_and_interval():
    assert build_parser().parse_args(["--once"]).once is True
    assert build_parser().parse_args(["--cycles", "3", "--interval", "0"]).cycles == 3
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--once", "--cycles", "2"])


def test_http_transport_login_payload_and_401_relogin_once():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("/login"):
            assert request.content == b"username=operator%40example.com&password=secret"
            return httpx.Response(200, json={"access_token": "memory-only"})
        if len(requests) == 2:
            return httpx.Response(401)
        return httpx.Response(201)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    transport = HttpTelemetryTransport("http://test", "operator@example.com", "secret", client=client, sleep=lambda _: None)
    event = TelemetryGenerator((sensor_config(),), random.Random(2), run_id="run").generate_cycle({ROBOT_ID: "active"}, 1, TIMESTAMP)[0]
    transport.login()
    result = transport.send(event)
    assert result.accepted is True
    assert len(requests) == 4


@pytest.mark.parametrize("status_code", [200, 201])
def test_http_success_statuses_are_accepted(status_code):
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status_code)))
    transport = HttpTelemetryTransport("http://test", "email", "password", client=client)
    transport.token = "token"
    event = TelemetryGenerator((sensor_config(),), random.Random(2), run_id="run").generate_cycle({ROBOT_ID: "active"}, 1, TIMESTAMP)[0]
    assert transport.send(event).accepted is True


@pytest.mark.parametrize("status_code", [403, 409, 422])
def test_http_terminal_responses(status_code):
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status_code, json={"detail": "conflict"})))
    transport = HttpTelemetryTransport("http://test", "email", "password", client=client)
    transport.token = "token"
    event = TelemetryGenerator((sensor_config(),), random.Random(2), run_id="run").generate_cycle({ROBOT_ID: "active"}, 1, TIMESTAMP)[0]
    result = transport.send(event)
    assert result.terminal is True


def test_http_404_disables_sensor_and_5xx_retries_are_bounded():
    attempts = []

    def handler(request):
        attempts.append(request)
        return httpx.Response(500)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    transport = HttpTelemetryTransport("http://test", "email", "password", client=client, sleep=lambda _: None)
    transport.token = "token"
    event = TelemetryGenerator((sensor_config(),), random.Random(2), run_id="run").generate_cycle({ROBOT_ID: "active"}, 1, TIMESTAMP)[0]
    result = transport.send(event)
    assert result.status_code == 500
    assert len(attempts) == 3

    missing = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(404)))
    transport = HttpTelemetryTransport("http://test", "email", "password", client=missing)
    transport.token = "token"
    assert transport.send(event).disable_sensor is True