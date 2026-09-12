from datetime import datetime, timedelta, timezone

from app.services.robot_health_policy import evaluate_robot_health, evaluate_sensor


AS_OF = datetime(2026, 9, 11, tzinfo=timezone.utc)


def test_battery_thresholds_are_explainable():
    assert evaluate_sensor("battery", 30, AS_OF, "percent", AS_OF).state.value == "healthy"
    assert evaluate_sensor("battery", 15, AS_OF, "percent", AS_OF).state.value == "warning"
    assert evaluate_sensor("battery", 14.9, AS_OF, "percent", AS_OF).state.value == "critical"
    assert evaluate_sensor("battery", 101, AS_OF, "percent", AS_OF).reason_codes == ("battery_invalid",)


def test_temperature_policy_and_freshness():
    assert evaluate_sensor("temperature", 45, AS_OF, "celsius", AS_OF).state.value == "healthy"
    assert evaluate_sensor("temperature", 50, AS_OF, "celsius", AS_OF).state.value == "warning"
    assert evaluate_sensor("temperature", 56, AS_OF, "celsius", AS_OF).state.value == "critical"
    stale = evaluate_sensor("temperature", 35, AS_OF - timedelta(seconds=301), "celsius", AS_OF)
    assert stale.state.value == "unknown"
    assert stale.freshness.value == "stale"


def test_operational_status_separation_and_maintenance_telemetry():
    healthy = evaluate_sensor("battery", 80, AS_OF, "percent", AS_OF)
    critical = evaluate_sensor("temperature", 56, AS_OF, "celsius", AS_OF)
    state, reasons = evaluate_robot_health("decommissioned", {"battery": healthy})
    assert state.value == "unknown"
    assert reasons == ("robot_decommissioned",)
    state, reasons = evaluate_robot_health("offline", {"battery": healthy})
    assert state.value == "unknown"
    assert reasons == ("robot_offline",)
    state, reasons = evaluate_robot_health("maintenance", {"battery": healthy})
    assert state.value == "healthy"
    assert reasons == ("robot_in_maintenance",)
    state, _ = evaluate_robot_health("maintenance", {"temperature": critical})
    assert state.value == "critical"