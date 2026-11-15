"""FP098: the "why it matters" line stops misfiring.

The significance line is picked by keyword rules in
story_intelligence._impact_hint. Two flaws, both seen live on
15 Nov 2026:

1. Substring matching: "ai" matched "said" (so nearly any story
   could get the technology line) and "race" matched "grace".
   Keywords now match as whole words/phrases.
2. The motorsport rule listed driver surnames, so "russell"
   matched every Russell Brand story and the motorsport line —
   checked first — won. Surnames and team names now only count
   alongside a motorsport context word (race, driver, circuit...).
"""
from story_intelligence import IMPACT_RULES, _impact_hint

MESSAGES = {name: message for name, _, message in IMPACT_RULES}
GENERIC = (
    "The immediate significance depends on what is confirmed next "
    "and whether the development produces wider consequences."
)


def hint(title, description=""):
    return _impact_hint(
        {"title": title, "description": description, "category": "World"}
    )


def test_russell_brand_is_not_motorsport():
    assert (
        hint("Russell Brand's wife shares message from disgraced comedian in prison")
        == GENERIC
    )


def test_russell_crowe_tribute_is_not_motorsport():
    assert (
        hint("On-ice 'Gladiator' tribute from Oilers' Levi draws Russell Crowe shoutout")
        == GENERIC
    )


def test_george_russell_with_anchor_is_motorsport():
    assert hint("Russell takes pole position in Brazil") == MESSAGES["motorsport"]


def test_driver_surname_with_race_context_is_motorsport():
    assert hint("Verstappen wins the race in Las Vegas") == MESSAGES["motorsport"]


def test_grace_does_not_supply_race_context():
    # "grace" contains "race" as a substring; whole-word matching
    # must not let it confirm the surname.
    assert hint("Russell Brand shows grace under pressure") == GENERIC


def test_said_does_not_trigger_technology():
    # "said" contains "ai" as a substring.
    assert hint("Local man said the festival was lovely") == GENERIC


def test_ai_chip_still_triggers_technology():
    assert hint("New AI chip promises faster phones") == MESSAGES["technology"]


def test_ferrari_road_car_is_not_motorsport():
    assert hint("Ferrari unveils new road car") != MESSAGES["motorsport"]
