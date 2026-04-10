import json
import logging
import os
import time
from typing import Any, Dict, List

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

logger = logging.getLogger("agent-commerce-core.normalizer")


# ------------------------------------------------------------------
# Internal Structured Output Schema (For Gemini's JSON Mode)
# ------------------------------------------------------------------
class ExtractedDataItem(BaseModel):
    """A strictly typed key-value pair to bypass additionalProperties restriction."""

    key: str = Field(
        description="The name of the attribute, specification, or data point."
    )
    value: str = Field(description="The extracted value. Always converted to a string.")


class NormalizedJsonOutput(BaseModel):
    """The exact JSON structure we force Gemini to generate internally."""

    title: str = Field(
        description="The main title or subject of the extracted web data."
    )
    core_summary: str = Field(
        description="A concise, objective summary of the technical or factual content."
    )
    trust_score: float = Field(
        description="Confidence score (0.0 to 1.0) indicating the fidelity and accuracy of the extraction based on the source text."
    )
    structured_data: List[ExtractedDataItem] = Field(
        description="A list of extracted key-value pairs representing specifications, documentation details, or public municipal data. Must not contain any prohibited insights."
    )


class NormalizedMarkdownOutput(BaseModel):
    """Internal schema to force Gemini to output a trust score alongside Markdown."""

    trust_score: float = Field(
        description="Confidence score (0.0 to 1.0) indicating the fidelity and accuracy of the extraction based on the source text."
    )
    content: str = Field(
        description="The extracted data strictly formatted in clean, well-structured Markdown."
    )


# ------------------------------------------------------------------
# Core Normalization Engine
# ------------------------------------------------------------------
class GeminiNormalizer:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning(
                "GEMINI_API_KEY is missing. Normalizer will fail if invoked."
            )

        self.client = genai.Client(api_key=api_key) if api_key else None
        self.flash_model = os.getenv("GEMINI_FLASH_MODEL", "gemini-3-flash")
        self.pro_model = os.getenv("GEMINI_PRO_MODEL", "gemini-3.1-pro")

    def _get_system_instruction(
        self, format_type: str, requested_fields: str | None = None
    ) -> str:
        """
        Defines the strict persona and compliance rules for the AI Engine.
        Dynamically adjusts instructions based on Lite GraphQL field requests.
        """
        base_instruction = (
            "You are a highly efficient B2B Data Normalization Infrastructure for AI agents. "
            "Your sole purpose is to extract, clean, and structure unstructured web content (e.g., technical docs, public data). "
            "CRITICAL COMPLIANCE RULE: You are strictly prohibited from analyzing, extracting, or outputting any "
            "financial data, trading signals, market analysis, or investment advice. If the input contains such data, "
            "ignore it completely and focus only on generic technical specifications or objective facts. "
            "ANTI-HALLUCINATION PROTOCOL: You must calculate a 'trust_score' (0.0 to 1.0) reflecting your extraction accuracy. "
            "Deduct points if the source text is ambiguous or lacks sufficient context. "
        )

        if format_type == "json":
            instruction = (
                base_instruction
                + "Output the extracted data strictly conforming to the provided JSON schema. "
            )
            if requested_fields:
                instruction += (
                    f"CRITICAL REQUIREMENT: The agent explicitly requested the following fields: [{requested_fields}]. "
                    "You MUST prioritize searching for and accurately extracting these specific data points. "
                    "Include them precisely within the output schema. "
                    "If a requested field does not exist in the source text, omit it rather than hallucinating fake data."
                )
            return instruction
        else:
            return (
                base_instruction
                + "Output the requested Markdown text inside the 'content' field of the JSON schema, alongside your 'trust_score'."
            )

    def normalize(
        self,
        raw_text: str,
        format_type: str = "markdown",
        use_pro_model: bool = False,
        requested_fields: str | None = None,
    ) -> tuple[bool, str, Dict[str, Any]]:
        """
        Executes the normalization process using Gemini.
        Returns:
            success (bool): Whether the extraction succeeded.
            data (str): The raw extracted string (Markdown or JSON string).
            metadata (dict): Processing metadata including potential error states.
        """
        if not self.client:
            return False, "", {"error": "Gemini Engine is not configured."}

        start_time = time.time()
        model_name = self.pro_model if use_pro_model else self.flash_model
        system_instruction = self._get_system_instruction(format_type, requested_fields)

        # Force application/json for BOTH formats to guarantee Trust Score extraction
        config_args = {
            "system_instruction": system_instruction,
            "temperature": 0.0,
            "response_mime_type": "application/json",
        }

        if format_type == "json":
            config_args["response_schema"] = NormalizedJsonOutput
        else:
            config_args["response_schema"] = NormalizedMarkdownOutput

        config = types.GenerateContentConfig(**config_args)

        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=f"Raw Web Content to Normalize:\n\n{raw_text}",
                config=config,
            )

            raw_response_text = response.text
            success = True
            error_message = None
            trust_score = 1.0

            try:
                parsed_json = json.loads(raw_response_text)
                trust_score = float(parsed_json.get("trust_score", 1.0))

                if format_type == "markdown":
                    output_content = parsed_json.get("content", "")
                else:
                    output_content = raw_response_text
            except json.JSONDecodeError:
                output_content = raw_response_text

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini Normalization failed: {error_msg}")

            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                return (
                    False,
                    "",
                    {
                        "error": "Rate limit exceeded on the upstream AI provider.",
                        "status_code": 429,
                    },
                )

            output_content = ""
            success = False
            error_message = error_msg
            trust_score = 0.0

        inference_time_ms = round((time.time() - start_time) * 1000)

        metadata = {
            "engine": model_name,
            "format": format_type,
            "inference_time_ms": inference_time_ms,
            "trust_score": trust_score,
        }
        if error_message:
            metadata["error"] = error_message

        return success, output_content, metadata


# Instantiate a singleton-like instance for the pipeline
normalizer = GeminiNormalizer()
