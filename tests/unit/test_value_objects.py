import pytest

from adrobot.domain.value_objects import (
    Alias,
    CampaignName,
    EmptyCampaignNameError,
    Geo,
    InvalidGeoError,
    InvalidOfferSharesError,
    distribute_offer_shares,
)


def test_geo_accepts_valid_alpha2_code() -> None:
    assert Geo("us").code == "US"


def test_geo_rejects_invalid_code() -> None:
    with pytest.raises(InvalidGeoError):
        Geo("USA")


def test_geo_rejects_unknown_two_letter_code() -> None:
    with pytest.raises(InvalidGeoError):
        Geo("ZZ")


def test_campaign_name_strips_whitespace() -> None:
    assert CampaignName("  My campaign  ").value == "My campaign"


def test_campaign_name_rejects_empty() -> None:
    with pytest.raises(EmptyCampaignNameError):
        CampaignName("   ")


def test_alias_is_unique_and_prefixed() -> None:
    a1 = Alias.generate()
    a2 = Alias.generate()
    assert a1.value != a2.value
    assert a1.value.startswith("adrobot-")


def test_distribute_offer_shares_sums_to_100_for_even_split() -> None:
    shares = distribute_offer_shares([1, 2])
    assert shares == {1: 50, 2: 50}
    assert sum(shares.values()) == 100


def test_distribute_offer_shares_sums_to_100_with_remainder() -> None:
    shares = distribute_offer_shares([1, 2, 3])
    assert sum(shares.values()) == 100
    assert shares[1] == 34  # первому достаётся остаток от округления
    assert shares[2] == 33
    assert shares[3] == 33


def test_distribute_offer_shares_single_offer_gets_100() -> None:
    assert distribute_offer_shares([42]) == {42: 100}


def test_distribute_offer_shares_rejects_empty_list() -> None:
    with pytest.raises(InvalidOfferSharesError):
        distribute_offer_shares([])


def test_distribute_offer_shares_rejects_duplicates() -> None:
    with pytest.raises(InvalidOfferSharesError):
        distribute_offer_shares([1, 1])
