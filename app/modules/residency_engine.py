"""Indian tax residency determination engine.

Classifies a person as Resident (Ordinarily Resident), RNOR, or Non-Resident
under the Income Tax Act 1961, per the rules recorded in
app/knowledge_base/india/nri_taxation.yaml::residency_rules.

That YAML stores the day-count thresholds only as human-readable prose
(e.g. "Present in India >= 182 days in the FY, ..."), not as structured
fields, so the thresholds below are Python constants mirroring that prose
exactly. The resulting tax-treatment flags (tax_on_global_income /
tax_on_india_income), which *are* structured in the YAML, are read from
the knowledge base at call time so they stay the single source of truth.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from app.models.user_profile import IndianResidentialStatus, ResidencyProfile
from app.utils.kb_loader import load_india_kb

# Section 6(1) Income Tax Act — basic residence test.
BASIC_TEST_DAYS_CURRENT_FY = 182
BASIC_TEST_DAYS_CURRENT_FY_ALT = 60
BASIC_TEST_DAYS_PRECEDING_4_FY = 365

# RNOR test — satisfying either condition makes a Resident an RNOR instead
# of Ordinarily Resident.
RNOR_MIN_NRI_YEARS_OUT_OF_10 = 9
RNOR_MAX_DAYS_PRECEDING_7_FY = 729

# nri_taxation.yaml residency_rules keys don't match the
# IndianResidentialStatus enum values 1:1 (e.g. "resident" -> "resident_ordinary").
_KB_RESIDENCY_RULE_KEY = {
    IndianResidentialStatus.RESIDENT: "resident_ordinary",
    IndianResidentialStatus.RNOR: "rnor",
    IndianResidentialStatus.NON_RESIDENT: "non_resident",
}


@dataclass
class ResidencyDetermination:
    status: IndianResidentialStatus
    tax_on_global_income: bool
    tax_on_india_income: bool
    meets_basic_residence_test: bool
    rnor_data_sufficient: bool
    reasoning: List[str] = field(default_factory=list)


def _tax_treatment_for(status: IndianResidentialStatus) -> tuple[bool, bool]:
    rule_key = _KB_RESIDENCY_RULE_KEY[status]
    rule = load_india_kb("nri_taxation.yaml")["residency_rules"][rule_key]

    tax_on_global_income = bool(rule["tax_on_global_income"])
    # resident_ordinary has no explicit tax_on_india_income key in the KB:
    # taxing global income already implies taxing India-sourced income.
    tax_on_india_income = bool(rule.get("tax_on_india_income", tax_on_global_income))

    return tax_on_global_income, tax_on_india_income


def determine_residential_status(
    days_in_india_current_fy: int,
    days_in_india_last_4_fy: int,
    years_as_nri_in_last_10_fy: Optional[int] = None,
    days_in_india_last_7_fy: Optional[int] = None,
) -> ResidencyDetermination:
    """Determine Indian tax residential status for a financial year.

    `years_as_nri_in_last_10_fy` and `days_in_india_last_7_fy` are needed
    only to distinguish RNOR from full Resident once the basic test is
    met; when omitted, the determination conservatively falls back to
    full Resident and flags `rnor_data_sufficient=False` so callers know
    to collect that data for an accurate answer rather than silently
    guessing RNOR (the more favourable status).
    """

    reasoning: List[str] = []

    meets_basic_test = days_in_india_current_fy >= BASIC_TEST_DAYS_CURRENT_FY or (
        days_in_india_current_fy >= BASIC_TEST_DAYS_CURRENT_FY_ALT
        and days_in_india_last_4_fy >= BASIC_TEST_DAYS_PRECEDING_4_FY
    )

    if not meets_basic_test:
        reasoning.append(
            f"Basic residence test not met: {days_in_india_current_fy} days in India this FY "
            f"(< {BASIC_TEST_DAYS_CURRENT_FY}), and not ({BASIC_TEST_DAYS_CURRENT_FY_ALT}+ days "
            f"this FY with {BASIC_TEST_DAYS_PRECEDING_4_FY}+ days in the preceding 4 FYs "
            f"[had {days_in_india_last_4_fy}])."
        )
        status = IndianResidentialStatus.NON_RESIDENT
        tax_on_global_income, tax_on_india_income = _tax_treatment_for(status)
        return ResidencyDetermination(
            status=status,
            tax_on_global_income=tax_on_global_income,
            tax_on_india_income=tax_on_india_income,
            meets_basic_residence_test=False,
            rnor_data_sufficient=True,
            reasoning=reasoning,
        )

    reasoning.append(
        f"Basic residence test met ({days_in_india_current_fy} days in India this FY)."
    )

    if years_as_nri_in_last_10_fy is None or days_in_india_last_7_fy is None:
        reasoning.append(
            "Insufficient data to check RNOR conditions (NRI status in preceding 10 FYs, "
            "days in India in preceding 7 FYs) — defaulting to Resident (Ordinarily "
            "Resident) as the conservative outcome. Provide this history for an accurate "
            "RNOR determination."
        )
        status = IndianResidentialStatus.RESIDENT
        tax_on_global_income, tax_on_india_income = _tax_treatment_for(status)
        return ResidencyDetermination(
            status=status,
            tax_on_global_income=tax_on_global_income,
            tax_on_india_income=tax_on_india_income,
            meets_basic_residence_test=True,
            rnor_data_sufficient=False,
            reasoning=reasoning,
        )

    is_rnor = (
        years_as_nri_in_last_10_fy >= RNOR_MIN_NRI_YEARS_OUT_OF_10
        or days_in_india_last_7_fy <= RNOR_MAX_DAYS_PRECEDING_7_FY
    )

    if is_rnor:
        reasoning.append(
            f"RNOR condition met: NRI for {years_as_nri_in_last_10_fy}/10 preceding FYs "
            f"(>= {RNOR_MIN_NRI_YEARS_OUT_OF_10}) or present {days_in_india_last_7_fy} days in "
            f"preceding 7 FYs (<= {RNOR_MAX_DAYS_PRECEDING_7_FY})."
        )
        status = IndianResidentialStatus.RNOR
    else:
        reasoning.append(
            f"RNOR conditions not met (NRI {years_as_nri_in_last_10_fy}/10 preceding FYs, "
            f"{days_in_india_last_7_fy} days in India in preceding 7 FYs) — Ordinarily Resident."
        )
        status = IndianResidentialStatus.RESIDENT

    tax_on_global_income, tax_on_india_income = _tax_treatment_for(status)

    return ResidencyDetermination(
        status=status,
        tax_on_global_income=tax_on_global_income,
        tax_on_india_income=tax_on_india_income,
        meets_basic_residence_test=True,
        rnor_data_sufficient=True,
        reasoning=reasoning,
    )


def determine_residency_from_profile(
    residency: ResidencyProfile,
    years_as_nri_in_last_10_fy: Optional[int] = None,
    days_in_india_last_7_fy: Optional[int] = None,
) -> ResidencyDetermination:
    """Convenience wrapper that reads day counts straight off a ResidencyProfile."""

    return determine_residential_status(
        days_in_india_current_fy=residency.days_in_india_current_fy,
        days_in_india_last_4_fy=residency.days_in_india_last_4_fy,
        years_as_nri_in_last_10_fy=years_as_nri_in_last_10_fy,
        days_in_india_last_7_fy=days_in_india_last_7_fy,
    )
