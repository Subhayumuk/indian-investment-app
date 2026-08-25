from types import SimpleNamespace

from app.utils.disclaimer_generator import DisclaimerGenerator

generator = DisclaimerGenerator()


def make_profile(tax_residency_country="Denmark"):
    return SimpleNamespace(tax_residency_country=tax_residency_country)


def test_base_disclaimers_always_present():
    disclaimers = generator.get_disclaimers(make_profile("Denmark"))
    joined = " ".join(disclaimers)
    assert "does not constitute financial, legal, or tax advice" in joined
    assert "does not store your personal financial data" in joined


def test_usa_residents_get_pfic_and_fbar_disclaimers():
    disclaimers = generator.get_disclaimers(make_profile("USA"))
    joined = " ".join(disclaimers)
    assert "PFIC" in joined
    assert "FBAR" in joined


def test_canada_residents_get_t1135_disclaimer():
    disclaimers = generator.get_disclaimers(make_profile("Canada"))
    assert any("T1135" in d for d in disclaimers)


def test_other_countries_get_only_base_disclaimers():
    denmark = generator.get_disclaimers(make_profile("Denmark"))
    usa = generator.get_disclaimers(make_profile("USA"))
    assert len(denmark) < len(usa)
