from jobmatch.profile.model import Profile
from jobmatch.profile.questionnaire import STEPS
from jobmatch.profile.store import load_profile, save_profile


def test_roundtrip(tmp_path, profile):
    path = save_profile(profile, tmp_path / "profile.yaml")
    loaded = load_profile(path)
    assert loaded == profile
    assert loaded.fingerprint() == profile.fingerprint()


def test_invalid_profile_returns_none(tmp_path):
    path = tmp_path / "profile.yaml"
    path.write_text("years_experience: -3\n")
    assert load_profile(path) is None
    assert load_profile(tmp_path / "missing.yaml") is None


def test_questionnaire_fields_exist_in_profile():
    fields = set(Profile.model_fields)
    for step in STEPS:
        for q in step.questions:
            assert q.field in fields, q.field
