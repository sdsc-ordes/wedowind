"""Schema inference errors."""


class SchemaInferenceError(RuntimeError):
    """Raised when schema cannot be inferred from a source file.

    This exception wraps failures from remote sample fetching, OMI inspection,
    Frictionless inference, or unsupported file formats during schema inference.
    """
