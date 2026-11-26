import assertpy
import pytest

from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.value_objects.marketplace import (
    agreement_id_value_object,
    agreement_request_id_value_object,
    offer_id_value_object,
)


class TestOfferIdValueObject:
    """Coverage for both AWS Marketplace offer identifier formats.

    AWS surfaces two shapes via ``marketplace-discovery.GetListing``:
    - legacy ``offer-<13 chars>`` (e.g. ``offer-jwqxgu6msev6q``)
    - new ``<25 chars>`` base32-like (e.g. ``3cvn2ei0u1ul606g43sdcipsy``)

    Both are accepted by downstream AWS APIs (``DescribeEntity``,
    ``marketplace-agreement``). The value object accepts both, plus any
    other non-empty alphanumeric identifier — see the module docstring
    for the rationale (matches ``agreement_id_value_object``'s policy).
    """

    def test_should_accept_legacy_offer_id_format(self):
        # Real example returned by GetListing on Ubuntu 24.04 LTS - Noble
        # (prodview-s4zvkzmlirbga).
        vo = offer_id_value_object.from_str("offer-jwqxgu6msev6q")
        assertpy.assert_that(vo.value).is_equal_to("offer-jwqxgu6msev6q")

    def test_should_accept_new_25_char_offer_id_format(self):
        # Real example returned by GetListing on Ubuntu Pro 24.04 LTS
        # (prodview-kbkyvwyqubv2g). Requiring an "offer-" prefix would
        # reject it and block every listing that uses the new format.
        vo = offer_id_value_object.from_str("3cvn2ei0u1ul606g43sdcipsy")
        assertpy.assert_that(vo.value).is_equal_to("3cvn2ei0u1ul606g43sdcipsy")

    def test_should_accept_short_placeholder(self):
        # We accept any non-empty alphanumeric identifier so that a
        # third format from AWS doesn't trap-door reject valid callers.
        vo = offer_id_value_object.from_str("offer-abc123")
        assertpy.assert_that(vo.value).is_equal_to("offer-abc123")

    def test_should_strip_surrounding_whitespace(self):
        vo = offer_id_value_object.from_str("  offer-jwqxgu6msev6q  ")
        assertpy.assert_that(vo.value).is_equal_to("offer-jwqxgu6msev6q")

    def test_should_reject_empty(self):
        with pytest.raises(DomainException, match="cannot be empty"):
            offer_id_value_object.from_str("")

    def test_should_reject_none(self):
        with pytest.raises(DomainException, match="cannot be empty"):
            offer_id_value_object.from_str(None)

    def test_should_reject_whitespace_only(self):
        with pytest.raises(DomainException, match="whitespace"):
            offer_id_value_object.from_str("   ")

    def test_should_reject_control_characters(self):
        # Path-traversal / injection hardening — reject anything outside
        # ASCII alphanumeric + hyphen.
        with pytest.raises(DomainException, match="expected alphanumeric"):
            offer_id_value_object.from_str("offer-abc\n123")

    def test_should_reject_forward_slash(self):
        with pytest.raises(DomainException, match="expected alphanumeric"):
            offer_id_value_object.from_str("offer-../etc/passwd")

    def test_should_reject_over_max_length(self):
        with pytest.raises(DomainException, match="too long"):
            offer_id_value_object.from_str("a" * 129)


class TestAgreementRequestIdValueObject:
    def test_should_accept_valid_id(self):
        vo = agreement_request_id_value_object.from_str("ar-1234567890abc")
        assertpy.assert_that(vo.value).is_equal_to("ar-1234567890abc")

    def test_should_reject_missing_prefix(self):
        with pytest.raises(DomainException, match="expected prefix 'ar-'"):
            agreement_request_id_value_object.from_str("agmt-x")

    def test_should_reject_empty(self):
        with pytest.raises(DomainException):
            agreement_request_id_value_object.from_str("")


class TestAgreementIdValueObject:
    def test_should_accept_valid_id_with_agmt_prefix(self):
        vo = agreement_id_value_object.from_str("agmt-1234567890abc")
        assertpy.assert_that(vo.value).is_equal_to("agmt-1234567890abc")

    def test_should_accept_any_non_empty_id(self):
        # AWS's ResourceId regex ([A-Za-z0-9_/-]+) does not guarantee a
        # prefix at the API level; we deliberately accept anything
        # non-empty to avoid a trap-door rejection of a valid agreement.
        vo = agreement_id_value_object.from_str("something-else-42")
        assertpy.assert_that(vo.value).is_equal_to("something-else-42")

    def test_should_reject_empty(self):
        with pytest.raises(DomainException):
            agreement_id_value_object.from_str("")
