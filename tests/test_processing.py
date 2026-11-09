from datetime import date

import pytest

from job_aggregator.domain.models import RawListing
from job_aggregator.processing.build_dedupe_key import build_dedupe_key
from job_aggregator.processing.normalize_listing import normalize_listing
from job_aggregator.processing.parse_experience import parse_experience_range
from job_aggregator.processing.parse_salary import parse_salary_lpa
from job_aggregator.processing.validate_listing import validate_listings

# (company, title, location, live dedupe_key) read from the live `jobs` table on 2026-11-08.
LIVE_KEYS = [
    ("Reliance Jio Infocomm Limited", "Software Development Engineer I", "Mumbai, Maharashtra",
     "reliance jio infocomm limited|software development engineer i|mumbai"),
    ("Equifax", "Software Engineer II", "Pune, Maharashtra", "equifax|software engineer ii|pune"),
    ("JPMorganChase", "Software Engineer II - Java - Springboot, React, RDBMS, Kubernetes", "Mumbai, Maharashtra",
     "jpmorganchase|software engineer ii java springboot react rdbms kubernetes|mumbai"),
    ("Seco Tools", "AI Engineer", "Pune, Maharashtra", "seco tools|ai engineer|pune"),
    ("General Mills", "Associate D&T Analyst - AI & Automation", "Powai, Mumbai, Maharashtra",
     "general mills|associate dt analyst ai automation|mumbai"),
    ("Ascent Groups", "Java Developer", "Hinjawadi, Pune, Maharashtra", "ascent groups|java developer|pune"),
    ("Blob Infotech Private Limited", "Software Developer (Java Spring Boot Developer)", "Remote",
     "blob infotech private limited|software developer java spring boot developer|remote"),
    ("Kreativ Web Solution", "Full Stack Developer (Java + Angular + Claude Code AI)", "Remote (India)",
     "kreativ web solution|full stack developer java angular claude code ai|remote"),
    ("JPMorganChase", "Software Engineer II - Fullstack (Java, React, AWS)", "Mumbai, Maharashtra",
     "jpmorganchase|software engineer ii fullstack java react aws|mumbai"),
    ("Priceline.com", "Associate Software Engineer", "Mumbai, Maharashtra",
     "priceline.com|associate software engineer|mumbai"),
    ("Blob Infotech Private Limited", "Java / Springboot Developer", "Remote",
     "blob infotech private limited|java springboot developer|remote"),
    ("Barclays", "Software Engineer - I (Java/J2EE developer)", "Pune, India",
     "barclays|software engineer i java j2ee developer|pune"),
    ("Mastercard", "Software Engineer II | Data & AI Platform", "Pune, Maharashtra",
     "mastercard|software engineer ii data ai platform|pune"),
    ("Amazon", "Software Development Engineer I", "Pune / Bengaluru / Hyderabad / Chennai / Delhi",
     "amazon|software development engineer i|pune"),
    ("Citi", "Java/J2EE Developer", "Pune, Maharashtra", "citi|java j2ee developer|pune"),
    ("Barclays", "Full Stack Developer", "Pune, Maharashtra", "barclays|full stack developer|pune"),
    ("PradeepIT Consulting Services", "Junior Java Developer", "India (Remote)",
     "pradeepit consulting services|junior java developer|remote"),
    ("Zebra Technologies", "Software Engineer I", "Pune, India", "zebra technologies|software engineer i|pune"),
]


@pytest.mark.parametrize(("company", "title", "location", "expected"), LIVE_KEYS)
def test_dedupe_key_reproduces_live_keys(app_settings, company, title, location, expected):
    p = app_settings.processing
    assert build_dedupe_key(company, title, location, p.known_cities, p.remote_location_words) == expected


def _raw(**overrides):
    data = {"source_id": "indeed", "title": "Java Developer", "company": "Acme",
            "apply_url": "https://in.indeed.com/viewjob?jk=1", "location": "Pune, Maharashtra"}
    data.update(overrides)
    return RawListing(**data)


def test_validation_rejects_missing_fields_and_excluded_company():
    listings = [
        _raw(), _raw(apply_url=""), _raw(title="  "), _raw(company="Excluded Corp Pvt Ltd"),
        _raw(apply_url="not-a-url"),
    ]
    outcome = validate_listings(listings, ["Excluded Corp"])
    assert len(outcome.accepted) == 1
    assert outcome.discard_reasons[("indeed", "missing apply_url")] == 2
    assert outcome.discard_reasons[("indeed", "missing title")] == 1
    assert outcome.discard_reasons[("indeed", "excluded company")] == 1
    assert outcome.discard_count_for("indeed") == 4


@pytest.mark.parametrize(
    ("text", "expected"),
    [("8-12 LPA", (8, 12)), ("₹ 6 Lakhs per annum", (6, 6)), ("INR 6,00,000 - 9,00,000 a year", (6, 9)),
     ("Stipend: 25,000 per month", (3, 3)), ("$80,000 - $100,000", (67.2, 84)), ("Not disclosed", (None, None)),
     ("1.2 Cr", (120, 120)), (None, (None, None)), ("1.2-1.5 lakh/month", (14.4, 18))],
)
def test_salary_parsing(app_settings, text, expected):
    assert parse_salary_lpa(text, app_settings.processing.usd_to_inr) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [("2-4 years", (2, 4)), ("0 - 2 Yrs", (0, 2)), ("3+ years of experience", (3, None)), ("Freshers welcome", (0, 0)),
     ("1 year", (1, 1)), ("no info", (None, None))],
)
def test_experience_parsing(text, expected):
    assert parse_experience_range(text) == expected


def test_normalise_with_stated_salary(app_settings, search_config):
    job = normalize_listing(
        _raw(salary_text="10-14 LPA", experience_text="1-3 years", skills=["Java", "java", " Spring "],
             employment_type="Full-time", posted_at=date(2026, 11, 7), description="<p>Build &amp; ship</p>"),
        app_settings.processing, search_config, board_base_url="https://in.indeed.com",
    )
    assert (job.salary_min_lpa, job.salary_max_lpa, job.salary_meets_min) == (10, 14, True)
    assert (job.min_yoe, job.max_yoe) == (1, 3)
    assert job.location_bucket == "pune" and job.work_mode == "onsite"
    assert job.employment_type == "full_time" and job.role_track == "java_backend"
    assert job.skills == ["Java", "Spring"]
    assert job.summary == "Build & ship"
    assert job.apply_url_kind == "board"
    assert job.dedupe_key == "acme|java developer|pune"


def test_normalise_missing_fields_and_unknown_values(app_settings, search_config):
    job = normalize_listing(_raw(location=None, title="Platform Specialist"), app_settings.processing, search_config)
    assert job.salary_min_lpa is None and job.salary_meets_min is None
    assert job.min_yoe is None and job.employment_type is None and job.work_mode is None
    assert job.location_bucket == "other" and job.role_track == "other"
    assert job.dedupe_key == "acme|platform specialist|"


@pytest.mark.parametrize(
    ("location", "override", "bucket"),
    [("Remote (India)", None, "remote_india"), ("Remote", None, "remote_india"),
     ("Remote", "remote_international", "remote_international"), ("Remote - US", None, "remote_international"),
     ("Worldwide, Remote", None, "remote_international"), ("Ahmedabad, Gujarat", None, "gujarat"),
     ("Bengaluru, Karnataka", None, "other"), ("Navi Mumbai", None, "mumbai")],
)
def test_location_buckets(app_settings, search_config, location, override, bucket):
    job = normalize_listing(_raw(location=location), app_settings.processing, search_config,
                            remote_bucket_override=override)
    assert job.location_bucket == bucket


def test_employer_apply_url_kind(app_settings, search_config):
    job = normalize_listing(_raw(apply_url="https://careers.acme.com/1"), app_settings.processing, search_config,
                            board_base_url="https://in.indeed.com")
    assert job.apply_url_kind == "employer"
