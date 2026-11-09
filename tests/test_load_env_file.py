"""The local .env.local loader: same variable names as Render, real environment wins."""

from job_aggregator.settings.load_env_file import find_env_file, load_env_file, parse_env_file_text
from job_aggregator.settings.read_secrets import read_secret_lists_from_environment


def test_parse_handles_comments_quotes_export_and_inline_comments():
    text = '# c\n\nA=1\nexport B="two words"\nC=\'x\'\nD=val # note\nbad line\n'
    assert parse_env_file_text(text) == {"A": "1", "B": "two words", "C": "x", "D": "val"}


def test_file_values_load_but_real_environment_wins(tmp_path):
    env_file = tmp_path / ".env.local"
    env_file.write_text("APIFY_TOKENS=t1,t2\nNTFY_TOPIC=from-file\nSUPABASE_URL=u\nSUPABASE_SERVICE_KEY=k\n",
                        encoding="utf-8")
    environ = {"NTFY_TOPIC": "from-real-env"}
    loaded = load_env_file(environ, env_file)
    assert sorted(loaded) == ["APIFY_TOKENS", "SUPABASE_SERVICE_KEY", "SUPABASE_URL"]
    secrets = read_secret_lists_from_environment(environ)
    assert secrets.service_tokens["apify"] == ["t1", "t2"]  # multiple tokens, same as deployed
    assert secrets.ntfy_topic == "from-real-env"


def test_missing_file_is_a_no_op(tmp_path):
    assert load_env_file({}, tmp_path / "absent") == []
    assert find_env_file({"JOB_AGGREGATOR_ENV_FILE": str(tmp_path / "x.env")}) == tmp_path / "x.env"
