"""Value objects: инварианты предметной области живут здесь, а не в сервисах."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

# ISO 3166-1 alpha-2 коды стран.
ISO_3166_1_ALPHA_2: frozenset[str] = frozenset(
    [
        "AD",
        "AE",
        "AF",
        "AG",
        "AI",
        "AL",
        "AM",
        "AO",
        "AQ",
        "AR",
        "AS",
        "AT",
        "AU",
        "AW",
        "AX",
        "AZ",
        "BA",
        "BB",
        "BD",
        "BE",
        "BF",
        "BG",
        "BH",
        "BI",
        "BJ",
        "BL",
        "BM",
        "BN",
        "BO",
        "BQ",
        "BR",
        "BS",
        "BT",
        "BV",
        "BW",
        "BY",
        "BZ",
        "CA",
        "CC",
        "CD",
        "CF",
        "CG",
        "CH",
        "CI",
        "CK",
        "CL",
        "CM",
        "CN",
        "CO",
        "CR",
        "CU",
        "CV",
        "CW",
        "CX",
        "CY",
        "CZ",
        "DE",
        "DJ",
        "DK",
        "DM",
        "DO",
        "DZ",
        "EC",
        "EE",
        "EG",
        "EH",
        "ER",
        "ES",
        "ET",
        "FI",
        "FJ",
        "FK",
        "FM",
        "FO",
        "FR",
        "GA",
        "GB",
        "GD",
        "GE",
        "GF",
        "GG",
        "GH",
        "GI",
        "GL",
        "GM",
        "GN",
        "GP",
        "GQ",
        "GR",
        "GS",
        "GT",
        "GU",
        "GW",
        "GY",
        "HK",
        "HM",
        "HN",
        "HR",
        "HT",
        "HU",
        "ID",
        "IE",
        "IL",
        "IM",
        "IN",
        "IO",
        "IQ",
        "IR",
        "IS",
        "IT",
        "JE",
        "JM",
        "JO",
        "JP",
        "KE",
        "KG",
        "KH",
        "KI",
        "KM",
        "KN",
        "KP",
        "KR",
        "KW",
        "KY",
        "KZ",
        "LA",
        "LB",
        "LC",
        "LI",
        "LK",
        "LR",
        "LS",
        "LT",
        "LU",
        "LV",
        "LY",
        "MA",
        "MC",
        "MD",
        "ME",
        "MF",
        "MG",
        "MH",
        "MK",
        "ML",
        "MM",
        "MN",
        "MO",
        "MP",
        "MQ",
        "MR",
        "MS",
        "MT",
        "MU",
        "MV",
        "MW",
        "MX",
        "MY",
        "MZ",
        "NA",
        "NC",
        "NE",
        "NF",
        "NG",
        "NI",
        "NL",
        "NO",
        "NP",
        "NR",
        "NU",
        "NZ",
        "OM",
        "PA",
        "PE",
        "PF",
        "PG",
        "PH",
        "PK",
        "PL",
        "PM",
        "PN",
        "PR",
        "PS",
        "PT",
        "PW",
        "PY",
        "QA",
        "RE",
        "RO",
        "RS",
        "RU",
        "RW",
        "SA",
        "SB",
        "SC",
        "SD",
        "SE",
        "SG",
        "SH",
        "SI",
        "SJ",
        "SK",
        "SL",
        "SM",
        "SN",
        "SO",
        "SR",
        "SS",
        "ST",
        "SV",
        "SX",
        "SY",
        "SZ",
        "TC",
        "TD",
        "TF",
        "TG",
        "TH",
        "TJ",
        "TK",
        "TL",
        "TM",
        "TN",
        "TO",
        "TR",
        "TT",
        "TV",
        "TW",
        "TZ",
        "UA",
        "UG",
        "UM",
        "US",
        "UY",
        "UZ",
        "VA",
        "VC",
        "VE",
        "VG",
        "VI",
        "VN",
        "VU",
        "WF",
        "WS",
        "YE",
        "YT",
        "ZA",
        "ZM",
        "ZW",
    ]
)


class InvalidGeoError(ValueError):
    """Код страны не соответствует ISO 3166-1 alpha-2."""


@dataclass(frozen=True, slots=True)
class Geo:
    """Код страны ISO 3166-1 alpha-2. Некорректный код не может существовать как объект."""

    code: str

    def __post_init__(self) -> None:
        normalized = self.code.strip().upper()
        if normalized not in ISO_3166_1_ALPHA_2:
            raise InvalidGeoError(
                f"'{self.code}' не является кодом страны в формате ISO 3166-1 alpha-2"
            )
        object.__setattr__(self, "code", normalized)

    def __str__(self) -> str:
        return self.code


class EmptyCampaignNameError(ValueError):
    """Название кампании не может быть пустым."""


@dataclass(frozen=True, slots=True)
class CampaignName:
    """Название кампании — непустая строка без крайних пробелов."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise EmptyCampaignNameError("Название кампании не может быть пустым")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Alias:
    """
    Технический идентификатор кампании, генерируется до обращения к Keitaro.

    Используется, чтобы найти кампанию в Keitaro при повторной обработке события
    (воркер мог упасть после создания кампании в Keitaro, но до сохранения keitaro_id).
    """

    value: str

    @classmethod
    def generate(cls) -> Alias:
        return cls(f"adrobot-{uuid.uuid4().hex[:16]}")

    def __str__(self) -> str:
        return self.value


class InvalidOfferSharesError(ValueError):
    """Список офферов для распределения долей некорректен."""


def distribute_offer_shares(offer_ids: list[int]) -> dict[int, int]:
    """
    Распределяет доли (в процентах) между офферами потока так, чтобы сумма была равна 100.

    Доли делятся поровну, остаток от целочисленного деления добавляется первым
    офферам в списке — так делает большинство редакторов потоков в трекерах,
    включая Keitaro: сумма долей всегда 100, а не 99 или 101 из-за округления.
    """
    if not offer_ids:
        raise InvalidOfferSharesError("Список офферов не может быть пустым")
    if len(set(offer_ids)) != len(offer_ids):
        raise InvalidOfferSharesError("Список офферов содержит дубликаты")

    count = len(offer_ids)
    base_share, remainder = divmod(100, count)
    shares: dict[int, int] = {}
    for index, offer_id in enumerate(offer_ids):
        shares[offer_id] = base_share + (1 if index < remainder else 0)
    return shares
