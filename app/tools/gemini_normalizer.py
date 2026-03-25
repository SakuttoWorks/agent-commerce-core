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
    structured_data: List[ExtractedDataItem] = Field(
        description="A list of extracted key-value pairs representing specifications, documentation details, or public municipal data. Must not contain any financial insights."
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

    def _get_system_instruction(self, format_type: str) -> str:
        """
        Defines the strict persona and compliance rules for the AI Engine.
        """
        base_instruction = (
            "You are a highly efficient B2B Data Normalization Infrastructure for AI agents. "
            "Your sole purpose is to extract, clean, and structure unstructured web content (e.g., technical docs, public data). "
            "CRITICAL COMPLIANCE RULE: You are strictly prohibited from analyzing, extracting, or outputting any "
            "financial data, trading signals, market analysis, or investment advice. If the input contains such data, "
            "ignore it completely and focus only on generic technical specifications or objective facts. "
        )

        if format_type == "json":
            return (
                base_instruction
                + "Output the extracted data strictly conforming to the provided JSON schema."
            )
        else:
            return (
                base_instruction
                + "Output the extracted data strictly in clean, well-structured Markdown format without any conversational filler."
            )

    def normalize(
        self, raw_text: str, format_type: str = "markdown", use_pro_model: bool = False
    ) -> tuple[bool, str, Dict[str, Any]]:
        """
        Executes the normalization process using Gemini.
        Returns:
            success (bool): Whether the extraction succeeded.
            data (str): The raw extracted string (Markdown or JSON string).
            metadata (dict): Processing metadata.
        """
        if not self.client:
            return False, "", {"error": "Gemini Engine is not configured."}

        start_time = time.time()
        model_name = self.pro_model if use_pro_model else self.flash_model
        system_instruction = self._get_system_instruction(format_type)

        # Configure model parameters
        config_args = {
            "system_instruction": system_instruction,
            "temperature": 0.0,  # Zero temperature for deterministic, factual extraction
        }

        # Enforce Structured Outputs if JSON is requested
        if format_type == "json":
            config_args["response_mime_type"] = "application/json"
            config_args["response_schema"] = NormalizedJsonOutput

        config = types.GenerateContentConfig(**config_args)

        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=f"Raw Web Content to Normalize:\n\n{raw_text}",
                config=config,
            )

            # Retrieve the raw text (which is a valid JSON string if format_type == "json")
            output_content = response.text
            success = True
            error_message = None

        except Exception as e:
            logger.error(f"Gemini Normalization failed: {e}")
            output_content = ""
            success = False
            error_message = str(e)

        inference_time_ms = round((time.time() - start_time) * 1000)

        metadata = {
            "engine": model_name,
            "format": format_type,
            "inference_time_ms": inference_time_ms,
        }
        if error_message:
            metadata["error"] = error_message

        return success, output_content, metadata


# Instantiate a singleton-like instance for the pipeline
normalizer = GeminiNormalizer()
