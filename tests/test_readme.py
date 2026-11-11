import json
import re
import shutil

from conftest import ROOT
from scp import readme



def _readme():
    return (ROOT / "README.md").read_text(encoding="utf-8")

TEMPLATE = readme.TEMPLATE.read_text(encoding="utf-8")

# Digits that may appear in the template outside placeholders, each with its reason.
ALLOWED_TOKENS = {
    "SSIC 2020",           # classification name
    "(2015)",              # chained-dollar base year in series names
    "M015761", "M015851",  # SingStat table ids
    "COVID-19",            # disease name
    "version 1.0",         # licence version
    "95%", "5%",           # names of the interval / significance level, not results
    "5th", "95th",         # percentile names
    "m2",                  # unit
    "### 1.", "### 2.", "### 3.", "### 4.",  # section numbers
}
YEAR = re.compile(r"(?<![\d.])(19|20)\d\d(?!\d|%|\.\d)")


def test_readme_is_rendered_from_results():
    assert _readme() == readme.render()


def test_readme_opens_with_disclaimer():
    assert TEMPLATE.splitlines()[0] == "Personal desk study on public data; not a BCA study."


def test_template_has_no_literal_numbers():
    text = readme.PLACEHOLDER.sub("", TEMPLATE)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"`[^`\n]*`", "", text)
    for tok in sorted(ALLOWED_TOKENS, key=len, reverse=True):
        text = text.replace(tok, "")
    text = YEAR.sub("", text)
    leftovers = re.findall(r".{0,20}\d.{0,20}", text)
    assert not leftovers, leftovers


def test_literal_number_check_catches_a_planted_number():
    bad = TEMPLATE.replace("## Results", "## Results\n\nSavings were 37% on site.", 1)
    text = YEAR.sub("", readme.PLACEHOLDER.sub("", bad))
    assert "37%" in text


def test_every_placeholder_resolves_to_a_results_file():
    found = readme.PLACEHOLDER.findall(TEMPLATE)
    assert len(found) > 50
    for fname, key, _ in found:
        assert (ROOT / "results" / fname).exists(), fname
        readme.lookup(ROOT / "results", fname, key)


def test_changing_a_result_changes_the_rendered_text(tmp_path):
    shutil.copy(ROOT / "results" / "productivity_trend.json", tmp_path / "productivity_trend.json")
    t = json.loads((tmp_path / "productivity_trend.json").read_text(encoding="utf-8"))
    t["va_per_hour_latest"] = 99.99
    (tmp_path / "productivity_trend.json").write_text(json.dumps(t), encoding="utf-8")
    out = readme.render(tmp_path, template="S${{productivity_trend.json:va_per_hour_latest|.2f}}")
    assert out == "S$99.99"


def test_render_booleans_and_list_indices(tmp_path):
    (tmp_path / "x.json").write_text(json.dumps({"a": [True, False], "b": {"c": 1234.5}}), encoding="utf-8")
    out = readme.render(tmp_path, template="{{x.json:a.0}} {{x.json:a.1}} {{x.json:b.c|,.0f}}")
    assert out == "yes no 1,234"
