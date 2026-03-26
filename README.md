# Agent-Commerce-Core | The Normalization Engine

**The high-performance compute engine and semantic extraction core for Agent-Commerce-OS.**

## 🏭 Role in Infrastructure

**Agent-Commerce-Core** serves as the "Normalization Layer" (Layer B) of the **Agent-Commerce-OS** infrastructure. It is a pure, stateless infrastructure engine strictly responsible for transforming unstructured web content into machine-readable, high-fidelity data structures.

While the [Gateway](https://github.com/SakuttoWorks/agent-commerce-gateway) (Layer A) manages public traffic, Polar.sh API authentication, and asynchronous usage metering, this core handles:

- **Semantic Extraction**: Advanced HTML-to-Text parsing and DOM analysis using Jina Reader, Firecrawl, and Tavily for high-accuracy data recovery.
- **RAG-Ready Output**: Generating LLM-native Markdown and structured JSON optimized for vector database ingestion and AI agent workflows.
- **Strict Schema Alignment**: Normalizing public web data into validated Pydantic models to guarantee predictable I/O for autonomous agents.

## 🛠 Tech Stack (Core Specifications)

- **Runtime**: Python 3.12+ (Standardized for 2026 Production Environments).
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) + Pydantic v2 - High-performance, strict type-safe API framework.
- **Build System**: [uv](https://github.com/astral-sh/uv) - Ultra-fast multi-stage Docker builds for minimal container footprints.
- **Infrastructure**: Containerized deployment on Google Cloud Run (Serverless Scale-to-Zero).
- **Security**: PyJWT-based dynamic tenant isolation.

## 🛡 Zero Trust Inter-service Communication

**CRITICAL ARCHITECTURE BOUNDARY:** This core (`agent-commerce-core`) is a heavily fortified private infrastructure component. Direct external access is strictly prohibited. It is designed to be invoked **exclusively** by the `agent-commerce-gateway`.

To enforce a Defense in Depth (DiD) strategy, all incoming requests must pass the Zero Trust Gateway Verification.
Any request lacking the following strictly enforced headers will be instantly dropped with a `403 Forbidden` response:

1. `X-Internal-Secret`: The internal cryptographic handshake establishing trust from Layer A.
2. `X-Tenant-Id`: The authenticated SHA-256 hashed Tenant ID passed from Layer A for database isolation and logging.

*Note: End-user API token validation (Polar.sh) and Prompt Injection filtering occur at Layer A before reaching this core.*

## 🚀 API Endpoint & Schema Definition

**Endpoint:** `POST /v1/normalize_web_data`

### 1. Example Request (`NormalizeRequest`)

*Must be routed through the internal network with Gateway headers.*

```bash
curl -X POST "https://agent-commerce-core-xd36uwybpa-an.a.run.app/v1/normalize_web_data" \
     -H "Content-Type: application/json" \
     -H "X-Internal-Secret: <INTERNAL_GATEWAY_SECRET>" \
     -H "X-Tenant-Id: <HASHED_TENANT_ID>" \
     -d '{
           "url": "https://docs.python.org/3/library/json.html",
           "format_type": "markdown"
         }'
```

### 2. Example Success Response (NormalizeResponse)

```json
{
  "success": true,
  "data": "# json — JSON encoder and decoder\n\nThis module exports an API familiar to users of the standard library...",
  "metadata": {
    "engine": "gemini-1.5-pro",
    "format": "markdown",
    "inference_time_ms": 1450
  }
}
```

### 3. Example AI-Optimized Error Response (AgentSemanticError)

Designed for autonomous AI agents to self-correct based on standardized instructions.

```json
{
  "error_type": "compliance_violation",
  "message": "Request blocked due to compliance policy. Forbidden term detected.",
  "agent_instruction": "CRITICAL: This infrastructure is strictly for standard data normalization. Alter your prompt and remove prohibited terms before retrying."
}
```

## ⚖️ Ethical Compliance

Strictly adheres to 2026 Data Privacy standards (GDPR/EU AI Act). Our engine only processes publicly accessible web information and operates completely stateless. It does not evaluate, store, or train on user prompts, and assumes no liability for the downstream utilization of the extracted data.

## 🔗 Project Ecosystem

- [SakuttoWorks Profile](https://github.com/SakuttoWorks) - Governance & Project Roadmap.
- [agent-commerce-gateway](https://github.com/SakuttoWorks/agent-commerce-gateway) - The Secure Edge Proxy (Layer A).

---

## 💖 Support the Project

If this infrastructure helped you save time or scale your AI agents, consider supporting the development! Your support helps keep this project highly maintained and secure.

[![Support via Polar.sh](https://img.shields.io/badge/Support_via-Polar.sh-blue?style=for-the-badge)](https://buy.polar.sh/polar_cl_ZI9H5fL8dQqcormOadiGDFDpS2Sxd1jT05jTX1vStWi)
[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-GitHub-ea4aaa?style=for-the-badge&logo=github)](https://github.com/sponsors/SakuttoWorks)

© 2026 Sakutto Works - Enabling the Semantic Web through Reliable Data Normalization.
