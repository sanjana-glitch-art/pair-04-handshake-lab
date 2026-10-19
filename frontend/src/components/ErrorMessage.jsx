// Bootstrap alert for a failed request; renders nothing when empty.
function ErrorMessage({ message }) {
  if (!message) {
    return null;
  }

  return (
    <div className="alert alert-danger" role="alert">
      {message}
    </div>
  );
}

export default ErrorMessage;
