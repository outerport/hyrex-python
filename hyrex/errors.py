"""Hyrex exception types.

Kept in a dependency-free module so callers can ``from hyrex import
HyrexTaskTimeout`` without importing the worker/executor machinery.
"""


class HyrexTaskTimeout(BaseException):
    """Raised in a worker when a task exceeds its ``timeout_seconds``.

    The executor arms ``signal.alarm(timeout_seconds)`` before running a task;
    when it fires, the SIGALRM handler raises this so the task unwinds.

    Subclasses ``BaseException`` (not ``Exception``) on purpose, like
    ``KeyboardInterrupt`` and ``asyncio.CancelledError``: a timeout is a
    control-flow signal that must unwind the task, so a broad ``except
    Exception`` in task code must never swallow it (which would let the task
    run past its deadline, since ``signal.alarm`` is one-shot). Code that needs
    to act on a timeout must catch it explicitly with ``except HyrexTaskTimeout``.
    """
