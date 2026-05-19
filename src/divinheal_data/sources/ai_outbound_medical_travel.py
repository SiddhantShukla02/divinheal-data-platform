# -----------------------------------------------------------------------------
# AI OUTBOUND MEDICAL TRAVEL SOURCE ADAPTER
# -----------------------------------------------------------------------------
# PURPOSE:
#   Uses Gemini to research source-backed outbound medical travel estimates.
#
# INPUT:
#   - Origin country name.
#   - Destination country names.
#   - Gemini API key.
#
# PROCESS:
#   - Builds a strict JSON-only research prompt.
#   - Calls Gemini once per origin country with all destination countries batched.
#   - Parses the model response as JSON.
#   - Validates that any non-empty estimate has source-backed evidence.
#   - Returns structured candidate results.
#
# OUTPUT:
#   - OutboundMedicalTravelBatchResult containing:
#       - origin country
#       - one result per destination country
#       - source-backed candidate estimates where available
#       - raw Gemini response text
#
# NOTES:
#   - Gemini is not treated as a source of truth.
#   - Values are only usable when the response includes source-backed evidence.
#   - Pipeline rows should still mark these fields as needs_review.
# -----------------------------------------------------------------------------

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types


GEMINI_MODEL_NAME = "gemini-2.5-flash"
GEMINI_MAX_OUTPUT_TOKENS = 8192

ALLOWED_ESTIMATE_TYPES = {"range", "directional", "insufficient_evidence"}
ALLOWED_CONFIDENCE_VALUES = {"high", "medium", "low", "insufficient"}
ALLOWED_STATUS_VALUES = {"needs_review", "insufficient_evidence"}


@dataclass(frozen=True)
class OutboundMedicalTravelEstimate:
    """Validated AI-assisted estimate result for one destination."""

    destination_country: str
    estimated_annual_outbound_medical_travel: str
    estimated_share_to_destination_pct: str
    estimate_type: str
    estimate_year_or_period: str
    confidence: str
    status: str
    source_outbound_stats: str
    sources: list[dict[str, str]]
    caveats: list[str]


@dataclass(frozen=True)
class OutboundMedicalTravelBatchResult:
    """Validated AI-assisted estimate batch for one origin country."""

    origin_country: str
    results: list[OutboundMedicalTravelEstimate]
    raw_text: str
    parsed_response: dict[str, Any]


def build_outbound_medical_travel_prompt(
    origin_country: str,
    destination_countries: list[str],
) -> str:
    """Build the Gemini research prompt for one origin and multiple destinations."""

    destination_country_list = "\n".join(
        f"- {destination_country}" for destination_country in destination_countries
    )

    return f"""
You are a medical tourism data analyst.

Task:
Find source-backed evidence for annual outbound medical travel from {origin_country} to each destination in this list:

{destination_country_list}

Rules:
- Do not invent estimates.
- Do not estimate from population size, income level, distance, geography, or general assumptions alone.
- Return "insufficient_evidence" only when there is no useful source-backed evidence about medical travel from {origin_country} to that destination.
- Do not use broad destination-level medical tourism totals unless the source clearly mentions {origin_country}.
- Do not use broad outbound travel/tourism numbers unless the source specifically refers to medical travel, medical tourism, healthcare travel, treatment travel, hospital patients, or medical visas.
- Prefer official reports, visa data, hospital reports, reputable news, academic/industry reports, or medical tourism market reports.
- If exact annual origin-to-destination patient volume is unavailable, but sources show relevant medical travel demand, destination popularity, hospital outreach, medical visa activity, or official source-market context, return a conservative directional range with low confidence and clear caveats.
- Directional estimates are allowed, but must still be tied to at least one source URL and must explain the reasoning in caveats.
- If sources conflict, include the conflict in caveats and choose the most defensible conservative range.
- Every non-empty estimate must include source URL, year/context, evidence summary, reported number/claim, and caveats.
- Source URLs must be real URLs from the evidence used. Do not cite a URL unless it directly supports the claim.
- Do not cite URLs from memory unless you are confident the URL exists and directly supports the claim.
- If you know the source name but are unsure of the exact URL, do not fabricate a URL. Return insufficient_evidence or use another reliable source with a real URL.
- Always return `estimated_annual_outbound_medical_travel` as a conservative rounded range or bucket, not a single exact number.
- If a source reports an exact number, convert it into a rounded range that reflects uncertainty.
- Do not use overly precise numbers in the final estimate field.
- Output valid JSON only.
- Do not wrap the JSON in markdown.
- Do not include commentary outside the JSON.
- Use the exact JSON keys shown below. Do not rename keys.

Standard estimate buckets:
- under 1,000
- under 5,000
- 5,000-10,000
- 10,000-25,000
- 25,000-50,000
- 50,000-100,000
- 100,000-250,000
- 250,000-500,000
- 500,000-1,000,000
- 1,000,000+

Rounding examples:
- 994,489 should become 500,000-1,000,000 or 900,000-1,000,000 if evidence is strong.
- 754,970 should become 700,000-800,000 or 500,000-1,000,000 depending on uncertainty.
- 450,000 should become 400,000-500,000.
- 12,000 should become 10,000-25,000.
- very small or unclear volumes may become under 5,000.

Required JSON format:
{{
  "origin_country": "{origin_country}",
  "results": [
    {{
      "destination_country": "Destination country name",
      "estimated_annual_outbound_medical_travel": "",
      "estimated_share_to_destination_pct": "",
      "estimate_type": "range|directional|insufficient_evidence",
      "estimate_year_or_period": "",
      "confidence": "high|medium|low|insufficient",
      "status": "needs_review|insufficient_evidence",
      "source_outbound_stats": "",
      "sources": [
        {{
          "source_name": "",
          "source_url": "",
          "evidence_summary": "",
          "reported_number_or_claim": ""
        }}
      ],
      "caveats": []
    }}
  ]
}}

Field rules:
- Include exactly one result object for each destination in the input destination list.
- `destination_country` must exactly match one of the destination names from the input list.
- `estimated_annual_outbound_medical_travel` must be a rounded range, directional bucket, or blank. Do not return precise single numbers.
- `estimated_share_to_destination_pct` may be a percentage/range or blank if unavailable.
- `estimate_type` must be "range" when the estimate is based on direct numeric evidence.
- `estimate_type` must be "directional" when the estimate is inferred from weaker source-backed evidence.
- Directional estimates should usually use `confidence` = "low" unless there is strong multi-source support.
- If `estimate_type` is "insufficient_evidence", then:
  - `estimated_annual_outbound_medical_travel` must be ""
  - `estimated_share_to_destination_pct` must be ""
  - `confidence` must be "insufficient"
  - `status` must be "insufficient_evidence"
  - `source_outbound_stats` must be ""
  - `sources` may be [] if no useful source was found.
- If `estimate_type` is not "insufficient_evidence", then:
  - `estimated_annual_outbound_medical_travel` must not be blank.
  - `confidence` must be "high", "medium", or "low".
  - `status` must be "needs_review".
  - `sources` must contain at least one source.
  - At least one source must include a non-empty `source_url`.
  - `source_outbound_stats` must summarize the evidence and include the source name/year/context.
- Prefer conservative estimates over inflated estimates.
""".strip()


def fetch_gemini_response_text(
    prompt: str,
    gemini_api_key: str,
) -> str:
    """Call Gemini and return response text."""

    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required when AI outbound estimates are enabled.")

    client = genai.Client(api_key=gemini_api_key)

    response = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
            response_mime_type="application/json",
        ),
    )

    if not response.text or not response.text.strip():
        raise ValueError("Gemini response text is empty.")

    return response.text.strip()


def parse_json_response_text(response_text: str) -> dict[str, Any]:
    """Parse Gemini JSON response text."""

    try:
        parsed_response = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini response text is not valid JSON.") from exc

    if not isinstance(parsed_response, dict):
        raise ValueError("Gemini JSON response must be an object.")

    return parsed_response


def has_source_url(sources: list[dict[str, str]]) -> bool:
    """Return whether at least one source has a non-empty URL."""

    return any(source.get("source_url", "").strip() for source in sources)


def validate_source_item(source: Any) -> dict[str, str]:
    """Validate and normalize one source item."""

    if not isinstance(source, dict):
        raise ValueError("Each source must be a JSON object.")

    return {
        "source_name": str(source.get("source_name", "")).strip(),
        "source_url": str(source.get("source_url", "")).strip(),
        "evidence_summary": str(source.get("evidence_summary", "")).strip(),
        "reported_number_or_claim": str(source.get("reported_number_or_claim", "")).strip(),
    }


def validate_estimate_result(
    result: Any,
    expected_destination_countries: set[str],
) -> OutboundMedicalTravelEstimate:
    """Validate one destination estimate result."""

    if not isinstance(result, dict):
        raise ValueError("Each destination result must be a JSON object.")

    destination_country = str(result.get("destination_country", "")).strip()
    if destination_country not in expected_destination_countries:
        raise ValueError(f"Unexpected destination country in AI result: {destination_country}")

    estimate_type = str(result.get("estimate_type", "")).strip()
    if estimate_type not in ALLOWED_ESTIMATE_TYPES:
        raise ValueError(f"Invalid estimate_type for {destination_country}: {estimate_type}")

    confidence = str(result.get("confidence", "")).strip()
    if confidence not in ALLOWED_CONFIDENCE_VALUES:
        raise ValueError(f"Invalid confidence for {destination_country}: {confidence}")

    status = str(result.get("status", "")).strip()
    if status not in ALLOWED_STATUS_VALUES:
        raise ValueError(f"Invalid status for {destination_country}: {status}")

    estimated_annual_outbound_medical_travel = str(
        result.get("estimated_annual_outbound_medical_travel", "")
    ).strip()
    estimated_share_to_destination_pct = str(
        result.get("estimated_share_to_destination_pct", "")
    ).strip()
    estimate_year_or_period = str(result.get("estimate_year_or_period", "")).strip()
    source_outbound_stats = str(result.get("source_outbound_stats", "")).strip()

    raw_sources = result.get("sources", [])
    if not isinstance(raw_sources, list):
        raise ValueError(f"sources must be a list for {destination_country}.")

    sources = [validate_source_item(source) for source in raw_sources]

    raw_caveats = result.get("caveats", [])
    if not isinstance(raw_caveats, list):
        raise ValueError(f"caveats must be a list for {destination_country}.")

    caveats = [str(caveat).strip() for caveat in raw_caveats if str(caveat).strip()]

    if estimate_type == "insufficient_evidence":
        if estimated_annual_outbound_medical_travel:
            raise ValueError(
                f"Insufficient evidence result cannot include an estimate for {destination_country}."
            )

        if estimated_share_to_destination_pct:
            raise ValueError(
                f"Insufficient evidence result cannot include share percentage for {destination_country}."
            )

        if confidence != "insufficient":
            raise ValueError(
                f"Insufficient evidence result must use insufficient confidence for {destination_country}."
            )

        if status != "insufficient_evidence":
            raise ValueError(
                f"Insufficient evidence result must use insufficient_evidence status for {destination_country}."
            )

    else:
        if not estimated_annual_outbound_medical_travel:
            raise ValueError(f"Source-backed estimate is missing for {destination_country}.")

        if confidence == "insufficient":
            raise ValueError(
                f"Source-backed estimate cannot use insufficient confidence for {destination_country}."
            )

        if status != "needs_review":
            raise ValueError(
                f"Source-backed estimate must use needs_review status for {destination_country}."
            )

        if not sources:
            raise ValueError(f"Source-backed estimate must include sources for {destination_country}.")

        if not has_source_url(sources):
            raise ValueError(
                f"Source-backed estimate must include at least one source URL for {destination_country}."
            )

        if not source_outbound_stats:
            raise ValueError(
                f"Source-backed estimate must include source_outbound_stats for {destination_country}."
            )

    return OutboundMedicalTravelEstimate(
        destination_country=destination_country,
        estimated_annual_outbound_medical_travel=estimated_annual_outbound_medical_travel,
        estimated_share_to_destination_pct=estimated_share_to_destination_pct,
        estimate_type=estimate_type,
        estimate_year_or_period=estimate_year_or_period,
        confidence=confidence,
        status=status,
        source_outbound_stats=source_outbound_stats,
        sources=sources,
        caveats=caveats,
    )


def validate_batch_response(
    parsed_response: dict[str, Any],
    expected_origin_country: str,
    expected_destination_countries: list[str],
) -> list[OutboundMedicalTravelEstimate]:
    """Validate a parsed Gemini batch response."""

    origin_country = str(parsed_response.get("origin_country", "")).strip()
    if origin_country != expected_origin_country:
        raise ValueError(
            f"Unexpected origin country in AI response: {origin_country}. "
            f"Expected: {expected_origin_country}."
        )

    raw_results = parsed_response.get("results", [])
    if not isinstance(raw_results, list):
        raise ValueError("Gemini JSON response must contain a results list.")

    expected_destination_set = set(expected_destination_countries)
    estimates = [
        validate_estimate_result(
            result=result,
            expected_destination_countries=expected_destination_set,
        )
        for result in raw_results
    ]

    returned_destination_set = {estimate.destination_country for estimate in estimates}
    if returned_destination_set != expected_destination_set:
        missing_destinations = sorted(expected_destination_set - returned_destination_set)
        extra_destinations = sorted(returned_destination_set - expected_destination_set)

        raise ValueError(
            "Gemini response must include exactly one result per destination. "
            f"Missing: {missing_destinations}. Extra: {extra_destinations}."
        )

    return estimates


def get_outbound_medical_travel_estimates_for_origin(
    origin_country: str,
    destination_countries: list[str],
    gemini_api_key: str,
) -> OutboundMedicalTravelBatchResult:
    """Fetch and validate outbound medical travel estimates for one origin country."""

    prompt = build_outbound_medical_travel_prompt(
        origin_country=origin_country,
        destination_countries=destination_countries,
    )
    raw_text = fetch_gemini_response_text(
        prompt=prompt,
        gemini_api_key=gemini_api_key,
    )
    parsed_response = parse_json_response_text(raw_text)
    estimates = validate_batch_response(
        parsed_response=parsed_response,
        expected_origin_country=origin_country,
        expected_destination_countries=destination_countries,
    )

    return OutboundMedicalTravelBatchResult(
        origin_country=origin_country,
        results=estimates,
        raw_text=raw_text,
        parsed_response=parsed_response,
    )