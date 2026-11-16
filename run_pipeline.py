"""
Run the whole pipeline with one command:

    python run_pipeline.py                 # load into the local practice database
    python run_pipeline.py --env supabase  # load into Supabase
    python run_pipeline.py --skip-download # use files already in data/raw/

Steps: EXTRACT -> TRANSFORM -> CHECK -> LOAD
If any ERROR-level check fails, nothing is loaded.
"""
import argparse
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

import checks
import config
import extract
import load
import transform


def setup_logging():
    """Print messages on screen AND save them to logs/pipeline.log."""
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(name)-18s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler("logs/pipeline.log", encoding="utf-8")],
    )


def main():
    parser = argparse.ArgumentParser(description="Athlete earnings data pipeline")
    parser.add_argument("--env", choices=["local", "supabase"], default="local",
                        help="where to load the data (default: local)")
    parser.add_argument("--skip-download", action="store_true",
                        help="use files already in data/raw/ instead of downloading")
    args = parser.parse_args()

    setup_logging()
    log = logging.getLogger("pipeline")
    run = {"run_id": uuid.uuid4().hex[:8], "environment": args.env,
           "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    log.info("===== Pipeline run %s started (environment: %s) =====", run["run_id"], args.env)

    conn = dialect = None
    try:
        # 1. EXTRACT
        if args.skip_download:
            paths = {n: os.path.join(config.RAW_DIR, f) for n, f in config.SOURCES.items()}
            log.info("Skipping download; using files in %s", config.RAW_DIR)
        else:
            paths = extract.extract_all()

        # 2. TRANSFORM
        tables = transform.transform_all(paths)

        # 3. CHECK
        results = checks.run_all_checks(tables)
        run["warnings"] = len(checks.warnings(results))
        failed = checks.errors(results)
        if failed:
            raise RuntimeError(f"{len(failed)} quality check(s) failed; nothing was loaded")

        # 4. LOAD
        conn, dialect = load.connect(args.env)
        run["rows_loaded"] = load.load_all(conn, dialect, tables)
        run["status"] = "SUCCESS"
        log.info("===== Pipeline finished: SUCCESS (%d warning(s)) =====", run["warnings"])
        return 0

    except Exception as error:
        run["status"] = "FAILED"
        run["message"] = str(error)
        log.error("===== Pipeline finished: FAILED - %s =====", error)
        return 1

    finally:
        # Record the run (even a failed one) so there's a history to monitor.
        try:
            if conn is None:
                conn, dialect = load.connect(args.env)
            load.record_run(conn, dialect, run)
            conn.close()
        except Exception as error:
            log.warning("Could not record this run in pipeline_runs: %s", error)


if __name__ == "__main__":
    sys.exit(main())
