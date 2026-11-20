# Dependencies

Python packages the project relies on, as pinned in the requirements files.

## Runtime (`requirements.txt`)

| Package | Constraint |
|---|---|
| `pandas` | `==2.2.3` |
| `SQLAlchemy` | `==2.0.36` |
| `psycopg2-binary` | `==2.9.10` |
| `python-dotenv` | `==1.0.1` |
| `tabulate` | `==0.9.0` |
| `matplotlib` | `==3.9.2` |

## Development (`requirements-dev.txt`)

| Package | Constraint |
|---|---|
| `pytest` | `==8.3.3` |
| `ruff` | `==0.8.4` |

Upgrade policy: bump one package at a time and run the full test suite.
