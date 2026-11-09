import pytest

from job_aggregator.credentials.credential_pool import CredentialPool
from job_aggregator.domain.models import NormalizedJob
from job_aggregator.linkedin.fetch_profile_posts import ProfilePost
from job_aggregator.linkedin.linkedin_profile_posts_fetcher import hiring_post_to_listing
from job_aggregator.linkedin.parse_hiring_post import parse_hiring_post
from job_aggregator.linkedin.resolve_short_link import ResolvedLink
from job_aggregator.processing.normalize_listing import normalize_listing
from job_aggregator.scoring.build_scorer import build_scorer, score_job_safely
from job_aggregator.scoring.gemini_scorer import GeminiApiError, GeminiScorer
from job_aggregator.scoring.rules_scorer import RulesScorer
from tests.conftest import FIXTURES


def _job(**overrides):
    data = {"dedupe_key": "acme|java developer|pune", "title": "Java Developer", "company": "Acme",
            "apply_url": "https://x", "source_id": "indeed", "source_url": "https://x", "location": "Pune",
            "location_bucket": "pune", "work_mode": "onsite", "min_yoe": 1, "max_yoe": 3,
            "salary_min_lpa": 10, "salary_max_lpa": 14, "skills": ["Java", "Spring Boot"]}
    data.update(overrides)
    return NormalizedJob(**data)


def test_good_fit_scores_high_with_reason(app_settings, search_config):
    result = RulesScorer(app_settings.scoring).score(_job(), search_config)
    assert result.score == 5
    assert "matches search" in result.reason.lower() and "meets" in result.reason


def test_each_criterion_lowers_the_score(app_settings, search_config):
    scorer = RulesScorer(app_settings.scoring)
    base = scorer.score(_job(), search_config).score
    over = scorer.score(_job(min_yoe=6, max_yoe=8), search_config)
    assert over.score < base and "above the 3-year limit" in over.reason
    far = scorer.score(_job(location="Chennai", location_bucket="other"), search_config)
    assert far.score < base and "outside preferences" in far.reason
    low_pay = scorer.score(_job(salary_min_lpa=3, salary_max_lpa=4), search_config)
    assert low_pay.score < base and "below the 8.2 minimum" in low_pay.reason
    off_topic = scorer.score(_job(title="Sales Manager", skills=["CRM"]), search_config)
    assert off_topic.score < base and "no search keyword matched" in off_topic.reason.lower()


def test_undisclosed_salary_is_neutral(app_settings, search_config):
    scorer = RulesScorer(app_settings.scoring)
    disclosed_ok = scorer.score(_job(), search_config)
    undisclosed = scorer.score(_job(salary_min_lpa=None, salary_max_lpa=None), search_config)
    assert "salary undisclosed" in undisclosed.reason
    # undisclosed neither rewards nor penalises: the difference is exactly the reward weight
    assert disclosed_ok.score - undisclosed.score <= app_settings.scoring.weights.salary_meets_min + 0.5


def test_identical_input_gives_identical_output(app_settings, search_config):
    scorer = RulesScorer(app_settings.scoring)
    assert scorer.score(_job(), search_config) == scorer.score(_job(), search_config)


def test_stripe_intern_example_is_flagged(app_settings, search_config):
    text = (FIXTURES / "post_stripe_intern.txt").read_text(encoding="utf-8")
    parsed = parse_hiring_post(text, app_settings.linkedin)
    listing = hiring_post_to_listing(ProfilePost("https://li/p/1", text, None), parsed,
                                     ResolvedLink("https://stripe.com/careers/1", True), "li_swadesh_kumar")
    job = normalize_listing(listing, app_settings.processing, search_config)
    result = RulesScorer(app_settings.scoring).score(job, search_config)
    assert "internship" in result.reason.lower()
    assert result.score <= 3


def test_batch_restricted_detected(app_settings, search_config):
    job = _job(title="Graduate Engineer Trainee", summary="Eligible batch: 2026 graduates only")
    result = RulesScorer(app_settings.scoring).score(job.model_copy(update={"title": "Graduate Engineer"}),
                                                     search_config)
    assert "graduating batch" in result.reason


def test_builder_uses_rules_only_when_model_is_disabled(app_settings):
    off = app_settings.scoring.model_copy(update={"gemini": app_settings.scoring.gemini.model_copy(
        update={"enabled": False})})
    assert isinstance(build_scorer(off, {}), RulesScorer)


def test_enabled_model_without_keys_falls_back_to_rules(app_settings):
    assert isinstance(build_scorer(app_settings.scoring, {}), RulesScorer)  # enabled in settings, no keys


def _gemini_settings(app_settings):
    return app_settings.scoring.model_copy(update={"gemini": app_settings.scoring.gemini.model_copy(
        update={"enabled": True})})


def test_model_used_for_borderline_when_enabled_and_available(app_settings, search_config):
    settings = _gemini_settings(app_settings)
    prompts = []

    def call(key, prompt):
        prompts.append(prompt)
        return {"score": 4, "reason": "Good backend fit"}

    scorer = GeminiScorer(RulesScorer(settings), CredentialPool("gemini", ["key-aaaa"]), settings.gemini, call)
    borderline = _job(location="Chennai", location_bucket="other", salary_min_lpa=None, salary_max_lpa=None)
    assert RulesScorer(settings).score(borderline, search_config).borderline
    result = scorer.score(borderline, search_config)
    assert result.score == 4 and "model review" in result.reason
    assert "Acme" in prompts[0] and "key-aaaa" not in prompts[0]
    assert scorer.score(_job(), search_config).reason.startswith("Matches")  # not borderline: rules only
    assert len(prompts) == 1


def test_all_tokens_exhausted_falls_back_to_rules(app_settings, search_config):
    settings = _gemini_settings(app_settings)

    def call(key, prompt):
        raise GeminiApiError(429, "RESOURCE_EXHAUSTED: quota exceeded")

    scorer = GeminiScorer(RulesScorer(settings), CredentialPool("gemini", ["k-aaaa", "k-bbbb"]), settings.gemini, call)
    job = _job(location="Chennai", location_bucket="other", salary_min_lpa=None, salary_max_lpa=None)
    assert scorer.score(job, search_config) == RulesScorer(settings).score(job, search_config)


def test_scoring_error_still_returns_storable_job(search_config):
    class Broken:
        def score(self, job, config):
            raise ZeroDivisionError("bad weight")

    job = score_job_safely(Broken(), _job(), search_config)
    assert job.fit_score == 3 and "Scoring failed" in job.fit_reason


def test_senior_title_without_stated_experience_is_penalised(app_settings, search_config):
    scorer = RulesScorer(app_settings.scoring)
    plain = scorer.score(_job(min_yoe=None, max_yoe=None), search_config)
    senior = scorer.score(_job(title="Senior Java Developer", min_yoe=None, max_yoe=None), search_config)
    assert senior.score < plain.score and "'senior' in the title" in senior.reason
    stated = scorer.score(_job(title="Senior Java Developer", min_yoe=1, max_yoe=2), search_config)
    assert "senior" not in stated.reason.lower()  # an explicit, acceptable range is trusted


def test_description_text_alone_does_not_count_as_a_keyword_match(app_settings, search_config):
    job = _job(title="Process Manager", skills=[], summary="We use AI and data engineer tooling daily")
    assert "no search keyword matched" in RulesScorer(app_settings.scoring).score(job, search_config).reason.lower()


def test_gemini_calls_are_spaced_out(app_settings, monkeypatch):
    import job_aggregator.scoring.gemini_scorer as module

    slept = []
    monkeypatch.setattr(module.time, "sleep", lambda seconds: slept.append(round(seconds, 1)))
    settings = _gemini_settings(app_settings).gemini.model_copy(update={"min_seconds_between_calls": 5})
    scorer = GeminiScorer(RulesScorer(app_settings.scoring), CredentialPool("gemini", ["k"]), settings,
                          call=lambda key, prompt: {"score": 3, "reason": "ok"})
    scorer._pace()
    scorer._pace()
    assert slept and slept[-1] <= 5 and len(slept) == 1  # the first call is immediate; the second waits


def test_prompt_wording_comes_from_the_config_file(app_settings, search_config, tmp_path):
    from job_aggregator.scoring.gemini_prompt import load_gemini_prompt
    from job_aggregator.scoring.gemini_scorer import build_prompt

    custom = tmp_path / "gemini_prompt.yaml"
    custom.write_text("instruction: |\n  CUSTOM WORDING. Answer with JSON.\n"
                      "data_template: |\n  Job: {job}\n  Criteria: {criteria}\n"
                      "  Rule-based estimate: {rules_score} ({rules_reason})\n", encoding="utf-8")
    job = _job()
    rules_result = RulesScorer(app_settings.scoring).score(job, search_config)
    text = build_prompt(job, search_config, rules_result, load_gemini_prompt(custom))
    assert text.startswith("CUSTOM WORDING. Answer with JSON.") and '"title": "Java Developer"' in text
    assert f"Rule-based estimate: {rules_result.score}" in text


def test_real_prompt_file_loads_and_keeps_the_json_contract():
    from job_aggregator.scoring.gemini_prompt import load_gemini_prompt
    from job_aggregator.scoring.gemini_scorer import DEFAULT_PROMPT_PATH

    prompt = load_gemini_prompt(DEFAULT_PROMPT_PATH)
    assert '{"score": <1-5>, "reason": "<one short sentence>"}' in prompt.instruction
    assert all(name in prompt.data_template for name in ("{criteria}", "{job}", "{rules_score}", "{rules_reason}"))


@pytest.mark.parametrize("body, expected", [
    ("instruction: hi\ndata_template: 'Job: {job} {criteria} {rules_score}'\n", "rules_reason"),
    ("instruction: hi\ndata_template: 'Job: {job} {criteria} {rules_score} {rules_reason} {oops}'\n", "stray brace"),
    ("instruction: ''\ndata_template: '{job} {criteria} {rules_score} {rules_reason}'\n", "instruction"),
])
def test_bad_prompt_file_stops_with_a_clear_message(tmp_path, body, expected):
    from job_aggregator.domain.errors import InvalidSettingsError
    from job_aggregator.scoring.gemini_prompt import load_gemini_prompt

    path = tmp_path / "gemini_prompt.yaml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(InvalidSettingsError, match=expected):
        load_gemini_prompt(path)
