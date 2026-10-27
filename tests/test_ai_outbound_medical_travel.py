# -----------------------------------------------------------------------------
# AI OUTBOUND MEDICAL TRAVEL SOURCE TESTS
# -----------------------------------------------------------------------------
# PURPOSE:
#   Verifies Gemini outbound medical travel prompt building, JSON parsing,
#   and response validation.
#
# INPUT:
#   Functions from divinheal_data.sources.ai_outbound_medical_travel.
#
# PROCESS:
#   - Tests prompt construction.
#   - Tests JSON response parsing.
#   - Tests valid source-backed estimates.
#   - Tests insufficient evidence responses.
#   - Tests invalid AI responses fail loudly.
#   - Tests high-level result creation while mocking the Gemini call.
#
# OUTPUT:
#   Passing tests for the AI outbound medical travel source adapter.
#
# NOTES:
#   - These tests do not call Gemini.
#   - These tests validate structure and safety gates only.
# -----------------------------------------------------------------------------

import json

import pytest

from divinheal_data.sources.ai_outbound_medical_travel import (
    OutboundMedicalTravelEstimate,
    build_outbound_medical_travel_prompt,
    get_outbound_medical_travel_estimates_for_origin,
    parse_json_response_text,
    validate_batch_response,
    validate_estimate_result,
)


VALID_BATCH_RESPONSE = {
    "origin_country": "Bangladesh",
    "results": [
        {
            "destination_country": "India",
            "estimated_annual_outbound_medical_travel": "100000-300000",
            "estimated_share_to_destination_pct": "",
            "estimate_type": "range",
            "estimate_year_or_period": "2024-2025",
            "confidence": "low",
            "status": "needs_review",
            "source_outbound_stats": (
                "Candidate estimate based on reported Bangladesh-to-India medical "
                "travel disruption and hospital patient inflow context."
            ),
            "sources": [
                {
                    "source_name": "Example News Source",
                    "source_url": "https://example.com/bangladesh-india-medical-travel",
                    "evidence_summary": "Reported Bangladeshi medical patient flow to India.",
                    "reported_number_or_claim": "Reported range or directional patient flow.",
                }
            ],
            "caveats": [
                "Estimate is directional and needs human review.",
            ],
        },
        {
            "destination_country": "Thailand",
            "estimated_annual_outbound_medical_travel": "",
            "estimated_share_to_destination_pct": "",
            "estimate_type": "insufficient_evidence",
            "estimate_year_or_period": "",
            "confidence": "insufficient",
            "status": "insufficient_evidence",
            "source_outbound_stats": "",
            "sources": [],
            "caveats": [
                "No source-backed origin-to-destination annual estimate found.",
            ],
        },
    ],
}


def test_build_outbound_medical_travel_prompt_contains_origin_and_destinations() -> None:
    prompt = build_outbound_medical_travel_prompt(
        origin_country="Bangladesh",
        destination_countries=["India", "Thailand"],
    )

    assert "Bangladesh" in prompt
    assert "- India" in prompt
    assert "- Thailand" in prompt
    assert "Output valid JSON only" in prompt
    assert "Do not invent estimates" in prompt
    assert '"estimated_annual_outbound_medical_travel"' in prompt


def test_parse_json_response_text_returns_dict() -> None:
    response_text = json.dumps(VALID_BATCH_RESPONSE)

    parsed_response = parse_json_response_text(response_text)

    assert parsed_response == VALID_BATCH_RESPONSE


def test_parse_json_response_text_rejects_invalid_json() -> None:
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_json_response_text("not json")


def test_parse_json_response_text_rejects_non_object_json() -> None:
    with pytest.raises(ValueError, match="must be an object"):
        parse_json_response_text(json.dumps(["bad", "shape"]))


def test_validate_estimate_result_accepts_source_backed_estimate() -> None:
    result = VALID_BATCH_RESPONSE["results"][0]

    estimate = validate_estimate_result(
        result=result,
        expected_destination_countries={"India", "Thailand"},
    )

    assert isinstance(estimate, OutboundMedicalTravelEstimate)
    assert estimate.destination_country == "India"
    assert estimate.estimated_annual_outbound_medical_travel == "100000-300000"
    assert estimate.estimate_type == "range"
    assert estimate.confidence == "low"
    assert estimate.status == "needs_review"
    assert estimate.sources[0]["source_url"] == (
        "https://example.com/bangladesh-india-medical-travel"
    )


def test_validate_estimate_result_accepts_insufficient_evidence() -> None:
    result = VALID_BATCH_RESPONSE["results"][1]

    estimate = validate_estimate_result(
        result=result,
        expected_destination_countries={"India", "Thailand"},
    )

    assert estimate.destination_country == "Thailand"
    assert estimate.estimated_annual_outbound_medical_travel == ""
    assert estimate.estimate_type == "insufficient_evidence"
    assert estimate.confidence == "insufficient"
    assert estimate.status == "insufficient_evidence"
    assert estimate.sources == []


def test_validate_estimate_result_rejects_unexpected_destination() -> None:
    result = {
        **VALID_BATCH_RESPONSE["results"][0],
        "destination_country": "Malaysia",
    }

    with pytest.raises(ValueError, match="Unexpected destination country"):
        validate_estimate_result(
            result=result,
            expected_destination_countries={"India", "Thailand"},
        )


def test_validate_estimate_result_rejects_source_backed_estimate_without_source_url() -> None:
    result = {
        **VALID_BATCH_RESPONSE["results"][0],
        "sources": [
            {
                "source_name": "Example News Source",
                "source_url": "",
                "evidence_summary": "Evidence summary exists.",
                "reported_number_or_claim": "Reported claim exists.",
            }
        ],
    }

    with pytest.raises(ValueError, match="at least one source URL"):
        validate_estimate_result(
            result=result,
            expected_destination_countries={"India", "Thailand"},
        )


def test_validate_estimate_result_rejects_source_backed_estimate_without_estimate() -> None:
    result = {
        **VALID_BATCH_RESPONSE["results"][0],
        "estimated_annual_outbound_medical_travel": "",
    }

    with pytest.raises(ValueError, match="Source-backed estimate is missing"):
        validate_estimate_result(
            result=result,
            expected_destination_countries={"India", "Thailand"},
        )


def test_validate_estimate_result_rejects_insufficient_result_with_estimate() -> None:
    result = {
        **VALID_BATCH_RESPONSE["results"][1],
        "estimated_annual_outbound_medical_travel": "100000-300000",
    }

    with pytest.raises(ValueError, match="cannot include an estimate"):
        validate_estimate_result(
            result=result,
            expected_destination_countries={"India", "Thailand"},
        )


def test_validate_batch_response_accepts_exact_destination_set() -> None:
    estimates = validate_batch_response(
        parsed_response=VALID_BATCH_RESPONSE,
        expected_origin_country="Bangladesh",
        expected_destination_countries=["India", "Thailand"],
    )

    assert [estimate.destination_country for estimate in estimates] == [
        "India",
        "Thailand",
    ]


def test_validate_batch_response_rejects_wrong_origin() -> None:
    response = {
        **VALID_BATCH_RESPONSE,
        "origin_country": "Nigeria",
    }

    with pytest.raises(ValueError, match="Unexpected origin country"):
        validate_batch_response(
            parsed_response=response,
            expected_origin_country="Bangladesh",
            expected_destination_countries=["India", "Thailand"],
        )


def test_validate_batch_response_rejects_missing_destination() -> None:
    response = {
        "origin_country": "Bangladesh",
        "results": [
            VALID_BATCH_RESPONSE["results"][0],
        ],
    }

    with pytest.raises(ValueError, match="exactly one result per destination"):
        validate_batch_response(
            parsed_response=response,
            expected_origin_country="Bangladesh",
            expected_destination_countries=["India", "Thailand"],
        )


def test_get_outbound_medical_travel_estimates_for_origin_builds_result(monkeypatch) -> None:
    def fake_fetch_gemini_response_text(prompt: str, gemini_api_key: str) -> str:
        assert "Bangladesh" in prompt
        assert "- India" in prompt
        assert "- Thailand" in prompt
        assert gemini_api_key == "fake-key"
        return json.dumps(VALID_BATCH_RESPONSE)

    monkeypatch.setattr(
        "divinheal_data.sources.ai_outbound_medical_travel.fetch_gemini_response_text",
        fake_fetch_gemini_response_text,
    )

    result = get_outbound_medical_travel_estimates_for_origin(
        origin_country="Bangladesh",
        destination_countries=["India", "Thailand"],
        gemini_api_key="fake-key",
    )

    assert result.origin_country == "Bangladesh"
    assert result.raw_text == json.dumps(VALID_BATCH_RESPONSE)
    assert result.parsed_response == VALID_BATCH_RESPONSE
    assert len(result.results) == 2
    assert result.results[0].destination_country == "India"
    assert result.results[1].destination_country == "Thailand"