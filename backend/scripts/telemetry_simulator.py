"""HTTP telemetry simulator for the seeded RoboOps fleet."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

import httpx

from app.streaming.kafka_producer import KafkaTelemetryTransport
from app.streaming.telemetry_events import TelemetryEventEnvelope

LOGGER = logging.getLogger("roboops.telemetry_simulator")
SUPPORTED_TYPES = {"battery", "temperature"}
EXPECTED_UNITS = {"battery": "percent", "temperature": "celsius"}


class SimulatorConfigError(ValueError):
    pass


class SimulatorTransportError(RuntimeError):
    pass


@dataclass(frozen=True)
class SensorConfig:
    sensor_id: uuid.UUID
    robot_id: uuid.UUID
    robot_code: str
    sensor_type: str
    unit: str


@dataclass(frozen=True)
class TelemetryEvent:
    sensor_id: uuid.UUID
    robot_id: uuid.UUID
    robot_code: str
    sensor_type: str
    unit: str
    value: float
    observed_at: datetime
    event_id: str
    source_event_id: str

    def payload(self) -> dict[str, object]:
        return {
            "sensor_id": str(self.sensor_id),
            "value": self.value,
            "observed_at": self.observed_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source_event_id": self.source_event_id,
        }

    def envelope(self, produced_at: datetime | None = None) -> TelemetryEventEnvelope:
        return TelemetryEventEnvelope(
            event_version=1,
            event_type="telemetry.reading",
            event_id=self.event_id,
            sensor_id=self.sensor_id,
            observed_at=self.observed_at,
            value=self.value,
            source_event_id=self.source_event_id,
            produced_at=produced_at or datetime.now(timezone.utc),
        )


@dataclass(frozen=True)
class IngestionResult:
    status_code: int
    accepted: bool
    terminal: bool = False
    disable_sensor: bool = False
    disable_robot: bool = False


@dataclass
class _SensorState:
    value: float


def parse_sensor_configuration(raw: str) -> tuple[SensorConfig, ...]:
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SimulatorConfigError("ROBOOPS_SIMULATOR_SENSORS must be valid JSON") from exc
    if not isinstance(entries, list) or not entries:
        raise SimulatorConfigError("ROBOOPS_SIMULATOR_SENSORS must be a non-empty JSON array")
    required = {"sensor_id", "robot_id", "robot_code", "sensor_type", "unit"}
    configs: list[SensorConfig] = []
    seen: set[uuid.UUID] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != required:
            raise SimulatorConfigError(f"sensor configuration entry {index} has invalid fields")
        try:
            sensor_id = uuid.UUID(str(entry["sensor_id"]))
            robot_id = uuid.UUID(str(entry["robot_id"]))
        except (ValueError, AttributeError, TypeError) as exc:
            raise SimulatorConfigError(f"sensor configuration entry {index} has invalid UUIDs") from exc
        values = [entry["robot_code"], entry["sensor_type"], entry["unit"]]
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise SimulatorConfigError(f"sensor configuration entry {index} has empty fields")
        robot_code, sensor_type, unit = (value.strip() for value in values)
        sensor_type = sensor_type.lower()
        unit = unit.lower()
        if sensor_type not in SUPPORTED_TYPES:
            raise SimulatorConfigError(f"unsupported simulator sensor type: {sensor_type}")
        if unit != EXPECTED_UNITS[sensor_type]:
            raise SimulatorConfigError(f"{sensor_type} sensors must use unit {EXPECTED_UNITS[sensor_type]}")
        if sensor_id in seen:
            raise SimulatorConfigError(f"duplicate sensor ID: {sensor_id}")
        seen.add(sensor_id)
        configs.append(SensorConfig(sensor_id, robot_id, robot_code, sensor_type, unit))
    return tuple(configs)


@dataclass(frozen=True)
class SimulatorConfig:
    api_url: str
    email: str
    password: str
    sensors: tuple[SensorConfig, ...]
    interval_seconds: float = 30.0
    seed: int = 20260910
    timeout_seconds: float = 10.0
    kafka_bootstrap_servers: str = ""
    kafka_topic: str = ""
    kafka_client_id: str = "roboops-telemetry-simulator"

    @classmethod
    def from_environment(cls, transport: str = "http") -> "SimulatorConfig":
        raw = os.environ.get("ROBOOPS_SIMULATOR_SENSORS", "")
        if not raw:
            raise SimulatorConfigError("ROBOOPS_SIMULATOR_SENSORS is required")
        try:
            interval = float(os.environ.get("ROBOOPS_SIMULATOR_INTERVAL_SECONDS", "30"))
            seed = int(os.environ.get("ROBOOPS_SIMULATOR_SEED", "20260910"))
            timeout = float(os.environ.get("ROBOOPS_SIMULATOR_TIMEOUT_SECONDS", "10"))
        except ValueError as exc:
            raise SimulatorConfigError("simulator numeric settings are invalid") from exc
        if interval < 0 or timeout <= 0:
            raise SimulatorConfigError("interval must be non-negative and timeout must be positive")
        values = {name: os.environ.get(name, "").strip() for name in ("ROBOOPS_API_URL", "ROBOOPS_SIMULATOR_EMAIL", "ROBOOPS_SIMULATOR_PASSWORD")}
        kafka_bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "").strip()
        kafka_topic = os.environ.get("KAFKA_TELEMETRY_TOPIC", "").strip()
        kafka_client_id = os.environ.get("KAFKA_CLIENT_ID", "roboops-telemetry-simulator").strip()
        if transport == "kafka" and (not kafka_bootstrap_servers or not kafka_topic or not kafka_client_id):
            raise SimulatorConfigError("KAFKA_BOOTSTRAP_SERVERS, KAFKA_TELEMETRY_TOPIC, and KAFKA_CLIENT_ID are required for Kafka transport")
        missing = [name for name, value in values.items() if not value]
        if transport == "http" and missing:
            raise SimulatorConfigError(f"missing required simulator settings: {', '.join(missing)}")
        return cls(values["ROBOOPS_API_URL"].rstrip("/"), values["ROBOOPS_SIMULATOR_EMAIL"], values["ROBOOPS_SIMULATOR_PASSWORD"], parse_sensor_configuration(raw), interval, seed, timeout, kafka_bootstrap_servers, kafka_topic, kafka_client_id)


class TelemetryGenerator:
    def __init__(self, sensors: tuple[SensorConfig, ...], rng: random.Random, run_id: str | None = None):
        self.sensors = sensors
        self.rng = rng
        self.run_id = run_id or uuid.uuid4().hex
        self.states: dict[uuid.UUID, _SensorState] = {}
        self.disabled_robots: set[uuid.UUID] = set()
        for sensor in sensors:
            initial = rng.uniform(72.0, 94.0) if sensor.sensor_type == "battery" else rng.uniform(20.0, 28.0)
            self.states[sensor.sensor_id] = _SensorState(initial)

    def disable_robot(self, robot_id: uuid.UUID) -> None:
        self.disabled_robots.add(robot_id)

    def recharge(self, sensor_id: uuid.UUID, value: float = 100.0) -> None:
        if not 0 <= value <= 100:
            raise ValueError("battery recharge must be between 0 and 100")
        self.states[sensor_id].value = value

    def _value(self, sensor: SensorConfig, status: str) -> float:
        state = self.states[sensor.sensor_id]
        if sensor.sensor_type == "battery":
            drain = {"active": (0.45, 0.75), "idle": (0.15, 0.30), "maintenance": (0.02, 0.08)}[status]
            state.value = max(0.0, min(100.0, state.value - self.rng.uniform(*drain) + self.rng.uniform(-0.12, 0.12)))
            return round(state.value, 2)
        target = {"active": 35.0, "idle": 27.0, "maintenance": 23.0}[status]
        state.value += (target - state.value) * 0.2 + self.rng.uniform(-0.25, 0.25)
        state.value = max(10.0, min(60.0, state.value))
        return round(state.value, 2)

    def generate_cycle(self, statuses: dict[uuid.UUID, str], cycle: int, observed_at: datetime) -> list[TelemetryEvent]:
        events: list[TelemetryEvent] = []
        for sensor in self.sensors:
            if sensor.robot_id in self.disabled_robots:
                continue
            status = statuses.get(sensor.robot_id)
            if status is None:
                self.disabled_robots.add(sensor.robot_id)
                LOGGER.warning("robot %s was not found; disabling it", sensor.robot_code)
                continue
            status = status.lower()
            if status == "decommissioned":
                self.disabled_robots.add(sensor.robot_id)
                LOGGER.warning("robot %s is decommissioned; disabling it", sensor.robot_code)
                continue
            if status == "offline":
                LOGGER.info("robot %s is offline; skipping cycle %s", sensor.robot_code, cycle)
                continue
            event_key = f"{self.run_id}:{sensor.sensor_id}:{cycle}".encode()
            digest = hashlib.sha256(event_key).hexdigest()
            event_id = f"sim-event:{digest}"
            source_event_id = f"sim-source:{digest}"
            events.append(TelemetryEvent(sensor.sensor_id, sensor.robot_id, sensor.robot_code, sensor.sensor_type, sensor.unit, self._value(sensor, status), observed_at, event_id, source_event_id))
        return events


class TelemetryTransport(Protocol):
    def send(self, event: TelemetryEvent) -> IngestionResult: ...


class HttpTelemetryTransport:
    def __init__(self, base_url: str, email: str, password: str, timeout: float = 10.0, max_attempts: int = 3, client: httpx.Client | None = None, sleep: Callable[[float], None] = time.sleep):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.client = client or httpx.Client(timeout=timeout)
        self.sleep = sleep
        self.token: str | None = None

    def login(self) -> None:
        response = self.client.post(f"{self.base_url}/api/v1/auth/login", data={"username": self.email, "password": self.password})
        if response.status_code != 200:
            raise SimulatorTransportError(f"login failed with status {response.status_code}")
        self.token = response.json().get("access_token")
        if not self.token:
            raise SimulatorTransportError("login response did not contain an access token")

    def _authorized(self, method: str, path: str, **kwargs) -> httpx.Response:
        relogin_used = False
        for attempt in range(self.max_attempts):
            if self.token is None:
                self.login()
            try:
                response = self.client.request(method, f"{self.base_url}{path}", headers={"Authorization": f"Bearer {self.token}"}, **kwargs)
            except httpx.RequestError as exc:
                if attempt + 1 == self.max_attempts:
                    raise SimulatorTransportError("network failure after bounded retries") from exc
                self.sleep(0.25 * (2**attempt))
                continue
            if response.status_code == 401 and not relogin_used:
                relogin_used = True
                self.login()
                continue
            if response.status_code >= 500 and attempt + 1 < self.max_attempts:
                self.sleep(0.25 * (2**attempt))
                continue
            return response
        raise SimulatorTransportError("request failed after bounded retries")

    def robot_statuses(self) -> dict[uuid.UUID, str]:
        response = self._authorized("GET", "/api/v1/robots")
        if response.status_code != 200:
            raise SimulatorTransportError(f"robot status request failed with status {response.status_code}")
        try:
            return {uuid.UUID(item["id"]): item["status"] for item in response.json()}
        except (KeyError, TypeError, ValueError) as exc:
            raise SimulatorTransportError("robot status response was invalid") from exc

    def send(self, event: TelemetryEvent) -> IngestionResult:
        response = self._authorized("POST", "/api/v1/telemetry/readings", json=event.payload())
        status = response.status_code
        if status in (200, 201):
            return IngestionResult(status, accepted=True)
        if status in (403, 422):
            return IngestionResult(status, accepted=False, terminal=True)
        if status == 404:
            return IngestionResult(status, accepted=False, terminal=True, disable_sensor=True)
        if status == 409:
            detail = response.json().get("detail", "") if response.content else ""
            return IngestionResult(status, accepted=False, terminal=True, disable_robot="decommissioned" in detail.lower())
        return IngestionResult(status, accepted=False, terminal=status < 500)


class TelemetrySimulator:
    def __init__(self, generator: TelemetryGenerator, transport: TelemetryTransport, sleep: Callable[[float], None] = time.sleep, clock: Callable[[], datetime] | None = None):
        self.generator = generator
        self.transport = transport
        self.sleep = sleep
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.disabled_sensors: set[uuid.UUID] = set()

    def cycle(self, cycle_number: int) -> None:
        status_provider = getattr(self.transport, "robot_statuses", None)
        statuses = status_provider() if status_provider is not None else {sensor.robot_id: "active" for sensor in self.generator.sensors}
        for event in self.generator.generate_cycle(statuses, cycle_number, self.clock()):
            if event.sensor_id in self.disabled_sensors or event.robot_id in self.generator.disabled_robots:
                continue
            result = self.transport.send(event)
            LOGGER.info("cycle=%s robot=%s sensor_type=%s value=%.2f event=%s status=%s", cycle_number, event.robot_code, event.sensor_type, event.value, event.source_event_id, result.status_code)
            if result.disable_sensor:
                self.disabled_sensors.add(event.sensor_id)
            if result.disable_robot:
                self.generator.disable_robot(event.robot_id)

    def run(self, cycles: int, interval_seconds: float) -> None:
        for cycle_number in range(1, cycles + 1):
            self.cycle(cycle_number)
            if cycle_number < cycles and interval_seconds:
                self.sleep(interval_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send realistic telemetry through the RoboOps HTTP API")
    parser.add_argument("--transport", choices=("http", "kafka"), default="http")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--once", action="store_true", help="send exactly one cycle")
    group.add_argument("--cycles", type=int, help="send exactly N cycles")
    parser.add_argument("--interval", type=float, help="seconds between cycles")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = SimulatorConfig.from_environment(args.transport)
    cycles = 1 if args.once or args.cycles is None else args.cycles
    interval = config.interval_seconds if args.interval is None else args.interval
    if cycles < 1:
        raise SystemExit("--cycles must be at least 1")
    if interval < 0:
        raise SystemExit("--interval must be non-negative")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.transport == "http":
        transport = HttpTelemetryTransport(config.api_url, config.email, config.password, config.timeout_seconds)
        transport.login()
    else:
        transport = KafkaTelemetryTransport(config.kafka_bootstrap_servers, config.kafka_topic, config.kafka_client_id, delivery_timeout_seconds=config.timeout_seconds)
    simulator = TelemetrySimulator(TelemetryGenerator(config.sensors, random.Random(config.seed)), transport)
    try:
        simulator.run(cycles, interval)
    finally:
        close = getattr(transport, "close", None)
        if close is not None:
            close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())