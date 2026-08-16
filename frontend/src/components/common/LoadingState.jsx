export default function LoadingState({ label = "Loading dashboard data..." } = {}) {
  return (
    <div className="state-panel loading-state" role="status">
      <div className="spinner" aria-hidden="true" />
      <p>{label}</p>
    </div>
  );
}
