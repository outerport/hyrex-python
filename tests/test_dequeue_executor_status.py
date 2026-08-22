from hyrex.dispatcher.sqlc.fetch_task import FETCH_TASK
from hyrex.dispatcher.sqlc.fetch_task_with_concurrency_limit import (
    FETCH_TASK_WITH_CONCURRENCY_LIMIT,
)


def test_dequeue_requires_a_running_executor():
    for query in (FETCH_TASK, FETCH_TASK_WITH_CONCURRENCY_LIMIT):
        assert "FROM hyrex_executor" in query
        assert "status = 'RUNNING'" in query
        assert "CROSS JOIN active_executor" in query
        assert "FOR SHARE" in query
