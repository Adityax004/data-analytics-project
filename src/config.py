from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DATABASE_DIR = ROOT_DIR / "database"
OUTPUT_DIR = ROOT_DIR / "outputs"
SQL_OUTPUT_DIR = OUTPUT_DIR / "sql"
TABLE_OUTPUT_DIR = OUTPUT_DIR / "tables"
FIGURE_OUTPUT_DIR = OUTPUT_DIR / "figures"
REPORT_OUTPUT_DIR = OUTPUT_DIR / "report"
POWERBI_DIR = ROOT_DIR / "powerbi"
POWERBI_IMPORT_DIR = POWERBI_DIR / "import_tables"
NOTEBOOK_DIR = ROOT_DIR / "notebooks"
DOCS_DIR = ROOT_DIR / "docs"
SQL_DIR = ROOT_DIR / "sql"

DATABASE_PATH = DATABASE_DIR / "ecommerce_analytics.sqlite"
ANALYSIS_DATE = "2026-01-01"
RANDOM_SEED = 42


def ensure_directories() -> None:
    for path in [
        RAW_DIR,
        PROCESSED_DIR,
        DATABASE_DIR,
        SQL_OUTPUT_DIR,
        TABLE_OUTPUT_DIR,
        FIGURE_OUTPUT_DIR,
        REPORT_OUTPUT_DIR,
        POWERBI_IMPORT_DIR,
        NOTEBOOK_DIR,
        DOCS_DIR,
        SQL_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)

