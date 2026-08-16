export default function ErrorState({
  message = "Something went wrong while loading dashboard data.",
  onRetry,
} = {}) {
  return (
    <div className="state-panel error-state" role="alert">
      <p>{message}</p>
      {onRetry ? (
        <button type="button" className="retry-button" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}
