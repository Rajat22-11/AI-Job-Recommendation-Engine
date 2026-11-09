from pathlib import Path

import pytest

from job_aggregator.domain.models import SearchConfig
from job_aggregator.settings.load_settings import load_settings

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def app_settings():
    return load_settings(REPO_ROOT / "config" / "settings.yaml")


@pytest.fixture
def search_config():
    return SearchConfig(
        keywords=["java", "spring boot", "backend", "full stack", "machine learning", "python"],
        locations=["Pune", "Mumbai", "Remote"],
        min_salary_lpa=8.2,
        max_required_yoe=3,
        max_job_age_days=30,
        excluded_companies=["Excluded Corp"],
    )
