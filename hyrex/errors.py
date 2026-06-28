"""Hyrex exception types.

Kept in a dependency-free module so callers can ``from hyrex import
HyrexTaskTimeout`` without importing the worker/executor machinery.
"""


class HyrexTaskTimeout(Exception):
    """Raised in a worker when a task exceeds its ``timeout_seconds``.

    The executor arms ``signal.alarm(timeout_seconds)`` before running a task;
    when it fires, the SIGALRM handler raises this so the task unwinds.
    """
