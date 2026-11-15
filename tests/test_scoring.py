from jobmatch.models import JobOffer, Modality, RemoteScope, Seniority
from jobmatch.scoring.scorer import score_offer
from jobmatch.scoring.semantic import HashingEmbedder, cosine, pack, rescale, unpack


def make_offer(**kw) -> JobOffer:
    base = dict(
        id="x",
        source="t",
        source_id="x",
        url="u",
        title="Backend Developer",
        company="Co",
        modality=Modality.REMOTE,
        remote_scope=RemoteScope.EUROPE,
    )
    base.update(kw)
    return JobOffer(**base)


def test_python_junior_beats_php_senior(profile):
    good = make_offer(
        title="Junior Python Developer",
        seniority=Seniority.JUNIOR,
        skills=["python", "fastapi", "postgresql"],
    )
    bad = make_offer(
        title="Senior PHP Developer",
        description="PHP and Laravel",
        seniority=Seniority.SENIOR,
        skills=["php", "laravel"],
    )
    s_good, s_bad = score_offer(profile, good, 0.8), score_offer(profile, bad, 0.3)
    assert s_good.total > 80
    assert s_bad.total < 30
    assert s_bad.penalties  # contiene 'php'


def test_breakdown_explains_skills(profile):
    offer = make_offer(skills=["python", "kubernetes", "go"])
    result = score_offer(profile, offer)
    detail = result.components["skills"]["detail"]
    assert "✔ python" in detail and "✘ go, kubernetes" in detail and "📚 kubernetes" in detail
    assert result.components["semantic"]["points"] == 12.5  # neutro sin embeddings
    assert "Skills" in result.summary()


def test_hard_filters(profile):
    assert score_offer(profile, make_offer(modality=Modality.ONSITE)).filtered
    assert score_offer(profile, make_offer(remote_scope=RemoteScope.OTHER)).filtered
    assert score_offer(profile, make_offer(company="Cárnica SA")).filtered
    assert not score_offer(profile, make_offer()).filtered
    profile.accepts_foreign_remote = False
    assert score_offer(profile, make_offer(remote_scope=RemoteScope.WORLDWIDE)).filtered


def test_salary_and_language(profile):
    low = score_offer(profile, make_offer(salary_min=14000, salary_max=14000))
    assert low.components["salary"]["points"] == 5.0
    german = score_offer(profile, make_offer(languages=["de"]))
    assert german.components["language"]["points"] == 0


def test_hashing_embedder_similarity():
    emb = HashingEmbedder()
    a, b, c = emb.embed(["python backend fastapi", "backend python django", "chef cocina"])
    assert cosine(a, b) > cosine(a, c)
    assert 0 <= rescale(cosine(a, b), emb) <= 1
    assert abs(cosine(unpack(pack(a)), a) - 1) < 1e-5


def test_internship_counts_as_junior(profile):
    profile.seniority = Seniority.INTERN
    for level in (Seniority.INTERN, Seniority.JUNIOR):
        result = score_offer(profile, make_offer(seniority=level))
        assert result.components["seniority"]["points"] == 15
    assert (
        score_offer(profile, make_offer(seniority=Seniority.MID)).components["seniority"]["points"]
        == 7.5
    )
    detail = score_offer(profile, make_offer(seniority=Seniority.JUNIOR)).components["seniority"]
    assert detail["detail"] == "Pide Junior, tú Prácticas"
