function LoadingSpinner({ label = "Loading..." }) {
  return (
    <div className="d-flex align-items-center gap-2 text-muted py-3" role="status">
      <div className="spinner-border spinner-border-sm" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export default LoadingSpinner;
