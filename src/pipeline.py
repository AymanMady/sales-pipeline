"""Pipeline orchestrator.

    python -m src.pipeline                # full run
    python -m src.pipeline --report-only  # rebuild the report from the database
"""

import argparse
import logging
import sys
import time

from src import clean, extract, load, report, transform
from src.config import SQL_DIR, setup_logging
from src.db import check_connection, query, run_sql_file

logger = logging.getLogger("pipeline")


def check_results(counts):
    """Verify the database holds what we think we put in it.

    A pipeline that never checks itself will eventually produce a wrong
    report without saying a word.
    """
    ok = True
    for table, expected in counts.items():
        actual = query(f"SELECT COUNT(*) AS n FROM core.{table}").iloc[0]["n"]
        if actual != expected:
            ok = False
        logger.info("  %-12s %5d rows (expected %d)", table, actual, expected)

    orphans = query("""
        SELECT COUNT(*) AS n
        FROM core.order_items i
        LEFT JOIN core.orders o ON o.order_id = i.order_id
        WHERE o.order_id IS NULL
    """).iloc[0]["n"]
    if orphans:
        ok = False
    logger.info("  orphan rows: %d", orphans)

    kpi = query("SELECT * FROM core.v_kpi").iloc[0]
    logger.info("  revenue %.2f EUR | %d orders | avg order %.2f EUR",
                kpi["revenue"], kpi["orders"], kpi["avg_order_value"])
    return ok


def run(report_only=False):
    start = time.perf_counter()

    if not check_connection():
        logger.error("PostgreSQL is not reachable. Start it with: make up")
        return 1

    if report_only:
        run_sql_file(SQL_DIR / "02_analytics.sql")
        report.build_report()
        return 0

    logger.info("--- schema ---")
    run_sql_file(SQL_DIR / "01_schema.sql")

    logger.info("--- extract ---")
    raw = extract.extract_all()

    logger.info("--- clean ---")
    customers, customers_log = clean.clean_customers(raw["customers"])
    products, products_log = clean.clean_products(raw["products"])
    orders, orders_log = clean.clean_orders(raw["orders"])

    logger.info("--- transform ---")
    tables, transform_log = transform.transform(customers, products, orders)

    logger.info("--- load ---")
    load.load_staging(raw)
    counts = load.load_core(tables)

    logger.info("--- analytics views ---")
    run_sql_file(SQL_DIR / "02_analytics.sql")

    logger.info("--- checks ---")
    ok = check_results(counts)

    logger.info("--- report ---")
    # Prefix each rule with its table, otherwise the report lists
    # "exact duplicate rows" three times with no way to tell them apart.
    quality_log = [
        (f"{source}: {reason}", count)
        for source, entries in [
            ("customers", customers_log),
            ("products", products_log),
            ("orders", orders_log),
            ("transform", transform_log),
        ]
        for reason, count in entries
    ]
    report.build_report(quality_log)

    elapsed = time.perf_counter() - start
    if not ok:
        logger.error("Finished in %.1fs, but some checks failed", elapsed)
        return 1
    logger.info("Done in %.1fs -> reports/report.md", elapsed)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Sales ETL pipeline")
    parser.add_argument("--report-only", action="store_true",
                        help="rebuild the report without reloading the CSVs")
    parser.add_argument("--debug", action="store_true", help="verbose logs")
    args = parser.parse_args()

    setup_logging(logging.DEBUG if args.debug else logging.INFO)
    return run(report_only=args.report_only)


if __name__ == "__main__":
    sys.exit(main())
