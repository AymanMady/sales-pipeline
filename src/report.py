"""Step 5: build the report.

Queries the analysis views and writes:
    reports/report.md            the readable report
    reports/*.csv                the same tables, for spreadsheets
    reports/revenue_by_month.png

No business logic here. The views define the numbers, this only formats them.
"""

import logging
from datetime import datetime
from decimal import Decimal

from src.config import REPORTS_DIR
from src.db import query

logger = logging.getLogger(__name__)

QUERIES = {
    "kpi": "SELECT * FROM core.v_kpi",
    "sales_by_month": "SELECT * FROM core.v_sales_by_month",
    "sales_by_product": "SELECT * FROM core.v_sales_by_product",
    "sales_by_category": "SELECT * FROM core.v_sales_by_category",
    "top_customers": "SELECT * FROM core.v_top_customers LIMIT 10",
}


def _to_float(table):
    """PostgreSQL NUMERIC comes back as Decimal, which does not format well."""
    for column in table.columns:
        if table[column].map(type).eq(Decimal).any():
            table[column] = table[column].astype(float)
    return table


def _table(data, headers):
    """Render selected columns as a Markdown table, using readable headers."""
    table = data[list(headers)].rename(columns=headers)
    # tabulate only shows missingval for None, so NaN has to become None first
    table = table.astype(object).where(table.notna(), None)
    return table.to_markdown(index=False, floatfmt=",.2f", intfmt=",", missingval="-")


def _chart(monthly):
    import matplotlib
    matplotlib.use("Agg")  # no display available in Docker or CI
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(figsize=(11, 4.5))
    axes.bar(monthly["month"], monthly["revenue"], color="#2E7D9A")
    axes.set_title("Revenue by month")
    axes.set_ylabel("Revenue (EUR)")
    axes.grid(axis="y", alpha=0.3)
    axes.set_axisbelow(True)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    name = "revenue_by_month.png"
    figure.savefig(REPORTS_DIR / name, dpi=120)
    plt.close(figure)
    return name


def build_report(quality_log=None):
    REPORTS_DIR.mkdir(exist_ok=True)

    results = {name: _to_float(query(sql)) for name, sql in QUERIES.items()}
    for name, table in results.items():
        table.to_csv(REPORTS_DIR / f"{name}.csv", index=False)

    kpi = results["kpi"].iloc[0]
    monthly = results["sales_by_month"]
    best_month = monthly.loc[monthly["revenue"].idxmax()]
    best_product = results["sales_by_product"].iloc[0]
    chart = _chart(monthly)

    lines = [
        "# Sales report",
        "",
        f"_Generated on {datetime.now():%d %B %Y at %H:%M} by the ETL pipeline._",
        f"_Covering {kpi['first_sale']:%d %b %Y} to {kpi['last_sale']:%d %b %Y}._",
        "",
        "## Key figures",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Revenue | **{kpi['revenue']:,.2f} EUR** |",
        f"| Orders | **{kpi['orders']:,}** |",
        f"| Average order value | **{kpi['avg_order_value']:,.2f} EUR** |",
        f"| Active customers | {kpi['active_customers']:,} |",
        f"| Items sold | {kpi['items_sold']:,} |",
        "",
        "> Average order value is revenue divided by distinct orders, not the",
        "> average order line. Cancelled and returned orders are excluded.",
        "",
        "## Revenue by month",
        "",
        _table(monthly, {
            "month": "Month",
            "revenue": "Revenue (EUR)",
            "orders": "Orders",
            "avg_order_value": "Avg order (EUR)",
            "growth_pct": "Growth (%)",
        }),
        "",
        f"![Revenue by month]({chart})",
        "",
        f"Best month: **{best_month['month']}** with {best_month['revenue']:,.2f} EUR.",
        "",
        "## Sales by product",
        "",
        _table(results["sales_by_product"], {
            "product_name": "Product",
            "category": "Category",
            "quantity_sold": "Quantity",
            "orders": "Orders",
            "revenue": "Revenue (EUR)",
            "revenue_share": "Share (%)",
        }),
        "",
        f"Best seller: **{best_product['product_name']}** "
        f"({best_product['revenue']:,.2f} EUR, {best_product['revenue_share']:.1f}% of revenue).",
        "",
        "## Sales by category",
        "",
        _table(results["sales_by_category"], {
            "category": "Category",
            "products": "Products",
            "quantity_sold": "Quantity",
            "revenue": "Revenue (EUR)",
        }),
        "",
        "## Top customers",
        "",
        _table(results["top_customers"], {
            "rank": "Rank",
            "customer": "Customer",
            "country": "Country",
            "orders": "Orders",
            "total_spent": "Total spent (EUR)",
            "avg_order_value": "Avg order (EUR)",
        }),
        "",
    ]

    if quality_log:
        lines += [
            "## Data quality",
            "",
            "Rows dropped during cleaning, rule by rule:",
            "",
            "| Rule | Rows dropped |",
            "|---|---|",
            *[f"| {reason} | {count} |" for reason, count in quality_log],
            f"| **Total** | **{sum(count for _, count in quality_log)}** |",
            "",
            "Nothing is dropped silently: the raw rows remain in the `staging` schema.",
            "",
        ]

    report = "\n".join(lines)
    (REPORTS_DIR / "report.md").write_text(report, encoding="utf-8")
    logger.info("Wrote reports/report.md")
    return report
