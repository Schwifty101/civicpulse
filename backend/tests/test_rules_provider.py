from app.providers.triage.rules import RuleBasedTriage
from app.schemas import Category, Priority

provider = RuleBasedTriage()


def test_never_raises_on_arbitrary_text():
    result = provider.triage("asdkj aslkdj laksjd", "Nowhere")
    assert result.category == Category.OTHER


def test_water_keywords_classified():
    result = provider.triage("Burst water pipe flooding the street since morning", "Street 5")
    assert result.category == Category.WATER


def test_electricity_keywords_classified():
    result = provider.triage("Transformer sparking, power outage in whole street", "Block A")
    assert result.category == Category.ELECTRICITY


def test_sanitation_keywords_classified():
    result = provider.triage("Garbage and sewage waste piling up, terrible smell", "Colony B")
    assert result.category == Category.SANITATION


def test_streetlights_keywords_classified():
    result = provider.triage("Streetlight is broken, whole dark street at night", "Sector 9")
    assert result.category == Category.STREETLIGHTS


def test_high_urgency_keyword_yields_high_priority():
    result = provider.triage("Emergency! Burst main flooding, danger to houses", "Street 12")
    assert result.priority == Priority.HIGH


def test_summary_never_exceeds_140_chars():
    long_text = "water leak " * 50
    result = provider.triage(long_text, "Somewhere")
    assert len(result.summary) <= 140


def test_confidence_within_bounds():
    result = provider.triage("Random unrelated text about nothing in particular", "X")
    assert 0.0 <= result.confidence <= 1.0
