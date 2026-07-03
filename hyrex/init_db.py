import os

from sqlalchemy import create_engine

from hyrex.dispatcher.sqlc import (
    create_cron_job_for_sql_query_sync,
    create_cron_job_for_sql_query,
    create_enums_sync,
    create_tables_sync,
    create_functions_sync,
)
from hyrex.dispatcher.sqlc.fill_historical_task_status_counts_table import FILL_HISTORICAL_TASK_STATUS_COUNTS_TABLE
from hyrex.dispatcher.sqlc.set_orphaned_task_execution_to_lost_and_retry import SET_ORPHANED_TASK_EXECUTION_TO_LOST_AND_RETRY
from hyrex.dispatcher.sqlc.set_executor_to_lost_if_no_heartbeat import SET_EXECUTOR_TO_LOST_IF_NO_HEARTBEAT
from hyrex.dispatcher.sqlc.advance_stuck_workflows import ADVANCE_STUCK_WORKFLOWS


def _fill_history_cron_enabled() -> bool:
    """Whether the observability-only FillHistoryTaskCountsTable cron should run.

    Enabled by default (keeps upstream Hyrex behavior). Set
    HYREX_FILL_HISTORY_CRON_ENABLED to a falsey value (0/false/no/off) to disable
    it. The cron Seq-scans the entire hyrex_task_run table every minute to feed
    the Hyrex Studio dashboard, and its cost grows with total table size.
    Outerport disables it in the worker/init launchers. The cron is always
    registered; this flag drives its `active` column, which init_postgres_db sets
    on every `hyrex init-db` AND every `run-worker` startup.
    """
    return os.environ.get("HYREX_FILL_HISTORY_CRON_ENABLED", "true").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _clean_sqlc_query(query: str) -> str:
    """Strip SQLC's `-- name:` directive line and `\\:` escapes so raw SQL runs."""
    lines = query.strip().split("\n")
    if lines and "-- name:" in lines[0]:
        lines = lines[1:]
    return "\n".join(lines).replace("\\:", ":")


def _system_cron_specs():
    """(jobname, schedule, command, active) for the Hyrex system crons.

    All are registered unconditionally so their schedule/command stay current; the
    config drives only FillHistoryTaskCountsTable's active flag (via
    HYREX_FILL_HISTORY_CRON_ENABLED, default on), which the scheduler honors
    (WHERE active = true). The maintenance crons are always active.
    """
    return [
        (
            "FillHistoryTaskCountsTable",
            "* * * * *",  # Every minute
            FILL_HISTORICAL_TASK_STATUS_COUNTS_TABLE,
            _fill_history_cron_enabled(),
        ),
        (
            "SetOrphanedRunningTaskToLost",
            "* * * * *",  # Every minute
            SET_ORPHANED_TASK_EXECUTION_TO_LOST_AND_RETRY,
            True,
        ),
        (
            "SetExecutorToLostIfNoHeartbeat",
            "* * * * *",  # Every minute
            SET_EXECUTOR_TO_LOST_IF_NO_HEARTBEAT,
            True,
        ),
        (
            "AdvanceStuckWorkflows",
            "*/2 * * * *",  # Every 2 minutes
            ADVANCE_STUCK_WORKFLOWS,
            True,
        ),
    ]


def init_postgres_db(conn_string):
    """Initialize the Postgres database with all required Hyrex tables and functions."""
    # Convert connection string to use psycopg3
    if conn_string.startswith("postgresql://"):
        conn_string = conn_string.replace("postgresql://", "postgresql+psycopg://", 1)
    elif conn_string.startswith("postgres://"):
        conn_string = conn_string.replace("postgres://", "postgresql+psycopg://", 1)

    # Create SQLAlchemy engine
    engine = create_engine(conn_string)

    with engine.begin() as conn:
        # Create enums (will skip if they already exist)
        try:
            create_enums_sync(conn)
        except Exception:
            pass  # Enums might already exist

        # Create tables and indexes
        create_tables_sync(conn)

        # Create functions and triggers
        create_functions_sync(conn)

        # Register the system crons. FillHistory's active flag comes from config
        # (the others are always active), so disabling it both stops new runs and
        # turns off a row a prior version left active.
        for jobname, schedule, command, active in _system_cron_specs():
            create_cron_job_for_sql_query_sync(
                conn,
                create_cron_job_for_sql_query.CreateCronJobForSqlQueryParams(
                    jobname=jobname,
                    schedule=schedule,
                    command=_clean_sqlc_query(command),
                    should_backfill=False,
                    active=active,
                ),
            )
