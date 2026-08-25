from app.models.user_profile import AccountType, IndianResidentialStatus, ResidencyProfile
from app.modules.residency_engine import (
    determine_residency_from_profile,
    determine_residential_status,
)


def test_fails_basic_test_is_non_resident():
    result = determine_residential_status(
        days_in_india_current_fy=40,
        days_in_india_last_4_fy=100,
    )
    assert result.status == IndianResidentialStatus.NON_RESIDENT
    assert result.meets_basic_residence_test is False
    assert result.tax_on_global_income is False
    assert result.tax_on_india_income is True


def test_meets_182_day_test_alone():
    result = determine_residential_status(
        days_in_india_current_fy=182,
        days_in_india_last_4_fy=0,
    )
    assert result.meets_basic_residence_test is True


def test_meets_60_plus_365_test():
    result = determine_residential_status(
        days_in_india_current_fy=60,
        days_in_india_last_4_fy=365,
    )
    assert result.meets_basic_residence_test is True


def test_60_days_alone_without_4fy_history_is_non_resident():
    result = determine_residential_status(
        days_in_india_current_fy=60,
        days_in_india_last_4_fy=364,
    )
    assert result.status == IndianResidentialStatus.NON_RESIDENT


def test_resident_without_rnor_data_defaults_to_resident_and_flags_insufficient_data():
    result = determine_residential_status(
        days_in_india_current_fy=200,
        days_in_india_last_4_fy=1000,
    )
    assert result.status == IndianResidentialStatus.RESIDENT
    assert result.rnor_data_sufficient is False
    assert result.tax_on_global_income is True


def test_rnor_via_nri_years_condition():
    result = determine_residential_status(
        days_in_india_current_fy=200,
        days_in_india_last_4_fy=1000,
        years_as_nri_in_last_10_fy=9,
        days_in_india_last_7_fy=1200,
    )
    assert result.status == IndianResidentialStatus.RNOR
    assert result.tax_on_global_income is False
    assert result.tax_on_india_income is True
    assert result.rnor_data_sufficient is True


def test_rnor_via_729_day_condition():
    result = determine_residential_status(
        days_in_india_current_fy=200,
        days_in_india_last_4_fy=1000,
        years_as_nri_in_last_10_fy=2,
        days_in_india_last_7_fy=729,
    )
    assert result.status == IndianResidentialStatus.RNOR


def test_ordinarily_resident_when_neither_rnor_condition_met():
    result = determine_residential_status(
        days_in_india_current_fy=200,
        days_in_india_last_4_fy=1000,
        years_as_nri_in_last_10_fy=2,
        days_in_india_last_7_fy=1200,
    )
    assert result.status == IndianResidentialStatus.RESIDENT
    assert result.tax_on_global_income is True
    assert result.tax_on_india_income is True


def test_determine_residency_from_profile_reads_day_counts_off_the_model():
    profile = ResidencyProfile(
        country_of_stay="USA",
        tax_residency_country="USA",
        days_in_india_current_fy=20,
        days_in_india_last_4_fy=80,
        account_types_held=[AccountType.NRE],
    )
    result = determine_residency_from_profile(profile)
    assert result.status == IndianResidentialStatus.NON_RESIDENT
