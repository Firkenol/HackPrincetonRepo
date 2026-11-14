"""Every physical constant must carry a real citation."""

from __future__ import annotations

from claimcheck import constants as K
from claimcheck.models import Chemistry, Routing, Verdict
from claimcheck import policy


def test_every_constant_has_a_complete_citation():
    constants = K.all_constants()
    assert len(constants) >= 20
    for c in constants:
        assert c.value > 0, c.key
        assert c.unit and c.description, c.key
        s = c.source
        assert s.title and s.publisher and s.locator, c.key
        assert s.url.startswith("https://"), c.key
        assert len(s.quote) >= 10, c.key
        assert s.accessed, c.key


def test_constant_keys_are_unique():
    keys = [c.key for c in K.all_constants()]
    # the same Constant object is reused where min, max and nominal coincide
    assert len(set(keys)) == len({id(c) for c in K.all_constants()})


def test_tables_only_use_known_chemistries():
    known = {c.value for c in Chemistry}
    for table in (K.MAX_WH_PER_L, K.MAX_WH_PER_KG, K.NOMINAL_CELL_VOLTAGE, K.MIN_CELL_VOLTAGE, K.MAX_CELL_VOLTAGE, K.MAX_PUBLISHED_STORAGE_YEARS):
        assert set(table) <= known
    assert set(K.IEC_SYSTEM_LETTERS.values()) <= known
    assert {ff.default_chemistry for ff in K.FORM_FACTORS.values()} <= known | {None}


def test_required_form_factors_are_present():
    assert {"18650", "21700", "AA", "AAA"} <= set(K.FORM_FACTORS)


def test_ceilings_sit_above_real_products_quoted_in_the_same_sources():
    # Panasonic NCR18650B datasheet: 676 Wh/L, 243 Wh/kg. Molicel P42A: 615 Wh/L, 230 Wh/kg.
    assert K.MAX_WH_PER_L["li-ion"].value > 676
    assert K.MAX_WH_PER_KG["li-ion"].value > 243


def test_verdict_and_routing_strings_are_exact():
    assert [v.value for v in Verdict] == ["Impossible", "Flag", "No red flags", "No checkable claim"]
    assert [r.value for r in Routing] == ["auto-resolvable", "needs human review"]
    assert policy.ROUTING_WHEN_NO_RED_FLAGS in {r.value for r in Routing}
    assert policy.ROUTING_WHEN_NO_CHECKABLE_CLAIM in {r.value for r in Routing}
