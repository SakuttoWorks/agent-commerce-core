# Agent-Commerce-Core | The Normalization Engine

**The high-performance compute engine and semantic extraction core for Agent-Commerce-OS.**

## 🏭 Role in Infrastructure
**Agent-Commerce-Core** serves as the "Normalization Layer" (Layer B) of the **Agent-Commerce-OS** infrastructure (formerly internally referred to as Project GHOST SHIP). It is the heavy-lifting engine responsible for transforming unstructured web content into machine-readable, high-fidelity data structures.

While the [Gateway](https://github.com/SakuttoWorks/agent-commerce-gateway) (Layer A) manages traffic and authentication, this core handles:

- **Semantic Extraction**: Advanced HTML-to-Text parsing and DOM analysis for high-accuracy data recovery from complex web sources.
- **RAG-Ready Output**: Generating LLM-native Markdown and JSON optimized for vector database ingestion and Retrieval-Augmented Generation (RAG) workflows.
- **Strict Schema Alignment**: Normalizing public utility and business data into validated Pydantic models for downstream automation and agentic tool-use.

## 🛠 Tech Stack (Core Specifications)
- **Runtime**: Python 3.12 (Standardized for 2026 Production Environments).
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - High-performance, type-safe API framework.
- **Infrastructure**: Containerized deployment on Google Cloud Run (Serverless Scaling).
- **Extraction Engine**: Hybrid processing using Jina Reader, Firecrawl, and proprietary structure-aware parsers.

## 🤖 Inter-service Communication & Security
This core is a private infrastructure component, designed to be invoked exclusively by the **Agent-Commerce-Gateway**.

- **Secure Handshake**: Requests are validated via a strict `X-Internal-Secret` header, ensuring only authorized gateway traffic is processed.
- **Discovery**: Real-time API specifications and context definitions are available at [api.sakutto.works/docs](https://api.sakutto.works/docs).
- **Ethical Compliance**: Strictly adheres to 2026 Data Privacy standards (GDPR/EU AI Act). Our engine only processes **publicly available information** and does not ingest or store PII (Personally Identifiable Information).

## 📂 Reference Implementation (Example)
To see this core in action, visit the [**agent-commerce-examples**](https://github.com/SakuttoWorks/agent-commerce-examples) repository, which contains production-grade normalization samples, such as public utility disposal regulations and municipal service schemas.

## 🔗 Project Ecosystem
- [**SakuttoWorks Profile**](https://github.com/SakuttoWorks/SakuttoWorks) - Governance & Project Roadmap.
- [**agent-commerce-gateway**](https://github.com/SakuttoWorks/agent-commerce-gateway) - The Secure Edge Proxy.

---
© 2026 Sakutto Works - Enabling the Semantic Web through Reliable Data Normalization.
