import { useCallback, useEffect, useState } from "react";
import Header from "../components/layout/Header.jsx";
import ErrorState from "../components/common/ErrorState.jsx";
import LoadingState from "../components/common/LoadingState.jsx";
import { useAuth } from "../auth/AuthContext.jsx";
import { getRobotHealth, getRobots, updateRobotStatus } from "../services/api.js";

const OPERATIONAL_STATUSES = ["active", "idle", "maintenance", "offline"];

function formatDate(value) {
	if (!value) return "-";
	const date = new Date(value);
	return Number.isNaN(date.getTime()) ? "-" : date.toLocaleDateString();
}

function statusLabel(status) {
	return status ? status.replaceAll("_", " ") : "Unknown";
}

function StatusBadge({ status }) {
	return <span className={`robot-status-badge status-${status || "unknown"}`}>{statusLabel(status)}</span>;
}

function RobotRow({ robot, canChangeStatus, onStatusChange }) {
	const [selectedStatus, setSelectedStatus] = useState(robot.status);
	const [pending, setPending] = useState(false);
	const [feedback, setFeedback] = useState(null);

	useEffect(() => {
		setSelectedStatus(robot.status);
	}, [robot.status]);

	const handleStatusChange = async (event) => {
		const nextStatus = event.target.value;
		const previousStatus = selectedStatus;
		if (pending || nextStatus === previousStatus) return;

		setSelectedStatus(nextStatus);
		setPending(true);
		setFeedback(null);
		try {
			const updatedRobot = await updateRobotStatus(robot.id, nextStatus);
			onStatusChange(updatedRobot);
		} catch (error) {
			setSelectedStatus(previousStatus);
			setFeedback({
				message: error.status === 403
					? "You do not have permission to change robot status."
					: "Unable to update robot status. Please try again.",
				type: error.status === 403 ? "permission" : "error",
			});
		} finally {
			setPending(false);
		}
	};

	const showControl = canChangeStatus && robot.status !== "decommissioned";

	return (
		<tr>
			<th scope="row">
				<span className="robot-name">{robot.name || "Unnamed robot"}</span>
				<span className="robot-code">{robot.robot_code || "-"}</span>
			</th>
			<td>{robot.serial_number || "-"}</td>
			<td>{robot.site_id || "-"}</td>
			<td>{robot.model_id || "-"}</td>
			<td><StatusBadge status={robot.status} /></td>
			<td>
				{robot.health ? (
					<div>
						<strong>{robot.health.health_state}</strong>
						<div>{robot.health.reason_codes.join(", ")}</div>
					</div>
				) : "unknown"}
			</td>
			<td>{formatDate(robot.installed_at)}</td>
			<td>
				{showControl ? (
					<div className="robot-action-cell">
						<select
							aria-label={`Change status for ${robot.robot_code || robot.name || "robot"}`}
							value={selectedStatus}
							disabled={pending}
							onChange={handleStatusChange}
						>
							{OPERATIONAL_STATUSES.map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}
						</select>
						{feedback ? <div className={`robot-row-feedback ${feedback.type}`} role="alert">{feedback.message}</div> : null}
					</div>
				) : feedback ? (
					<div className={`robot-row-feedback ${feedback.type}`} role="alert">{feedback.message}</div>
				) : (
					<span className="robot-no-action">-</span>
				)}
			</td>
		</tr>
	);
}

export default function Robots() {
	const { user } = useAuth();
	const [robots, setRobots] = useState([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);
	const canChangeStatus = user?.role === "operator" || user?.role === "admin";

	const loadRobots = useCallback(async () => {
		setLoading(true);
		setError(null);
		try {
			const [robotData, healthData] = await Promise.all([getRobots(), getRobotHealth()]);
			setRobots(robotData.map((robot) => ({ ...robot, health: healthData?.robots?.find((item) => item.robot_id === robot.id) })));
		} catch (requestError) {
			setError(requestError);
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		loadRobots();
	}, [loadRobots]);

	const replaceRobot = (updatedRobot) => {
		setRobots((currentRobots) => currentRobots.map((robot) => (
			robot.id === updatedRobot.id ? { ...updatedRobot, health: robot.health } : robot
		)));
	};

	return (
		<section className="page robots-page">
			<Header title="Robots" />
			<div className="robots-heading">
				<div>
					<div className="eyebrow">Fleet operations</div>
					<h2>Robots</h2>
				</div>
				{!loading && !error ? <p className="robots-count">{robots.length} {robots.length === 1 ? "robot" : "robots"}</p> : null}
			</div>
			{loading ? <LoadingState label="Loading robots..." /> : null}
			{!loading && error ? <ErrorState message="Unable to load robots. Please try again." onRetry={loadRobots} /> : null}
			{!loading && !error && robots.length === 0 ? <div className="state-panel"><p>No robots found.</p></div> : null}
			{!loading && !error && robots.length > 0 ? (
				<div className="robots-table-container">
					<table className="robots-table">
						<thead>
							<tr>
								<th scope="col">Robot</th>
								<th scope="col">Serial Number</th>
								<th scope="col">Site ID</th>
								<th scope="col">Model ID</th>
								<th scope="col">Status</th>
								<th scope="col">Telemetry Health</th>
								<th scope="col">Installed</th>
								<th scope="col">Actions</th>
							</tr>
						</thead>
						<tbody>
							{robots.map((robot) => (
								<RobotRow key={robot.id} robot={robot} canChangeStatus={canChangeStatus} onStatusChange={replaceRobot} />
							))}
						</tbody>
					</table>
				</div>
			) : null}
		</section>
	);
}
