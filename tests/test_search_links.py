from urllib.parse import parse_qs, urlparse

from jobmatch.models import Seniority
from jobmatch.search_links import build_links, search_keywords


def test_keywords_from_title_or_skills(profile):
    assert search_keywords(profile) == "Backend Developer Python"
    profile.desired_title = ""
    assert search_keywords(profile) == "python backend developer"


def test_links_use_profile(profile):
    profile.seniority = Seniority.INTERN
    profile.city = "Málaga"
    links = {link.portal: link.url for link in build_links(profile)}
    assert set(links) == {"LinkedIn", "InfoJobs", "Indeed", "Tecnoempleo"}
    linkedin = parse_qs(urlparse(links["LinkedIn"]).query)
    assert linkedin["keywords"] == ["Backend Developer Python"]
    assert linkedin["location"] == ["Málaga"]
    assert linkedin["f_E"] == ["1,2"] and linkedin["f_WT"] == ["2,3"]
    infojobs = parse_qs(urlparse(links["InfoJobs"]).query)
    assert infojobs["keyword"] == ["prácticas Backend Developer Python"]
