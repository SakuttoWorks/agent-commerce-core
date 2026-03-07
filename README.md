# Agent-Commerce-Core | The Normalization Engine
**The high-performance compute engine and semantic extraction core for Project GHOST SHIP.**

## 🏭 Role in Infrastructure
**Agent-Commerce-Core** is the "Normalization Layer" (Layer B) of the Project GHOST SHIP infrastructure. While the [Gateway](https://github.com/SakuttoWorks/agent-commerce-gateway) handles request validation and rate-limiting, this core repository manages heavy-duty data processing:

- **Semantic Extraction**: Advanced web scraping and HTML-to-Text parsing.
- **RAG Pipeline**: Generating LLM-native Markdown/JSON optimized for vector ingestion.
- **Schema Alignment**: Normalizing unstructured web data into strict Pydantic models.

## 🛠 Tech Stack (Core Specifications)
- **Runtime**: Python 3.13+ (Optimized for async performance and GIL-free execution).
- **Framework**: FastAPI / Pydantic V2.
- **Infrastructure**: Google Cloud Run (Serverless Container).
- **Extraction Logic**: Integrated with Jina Reader, Firecrawl, and custom DOM parsers.

## 🤖 Inter-service Communication
This core is designed to be invoked exclusively by the **Agent-Commerce-Gateway**.
- **Discovery**: API schemas are synchronized via [llms-full.txt](https://sakutto.works/llms-full.txt).
- **Security**: Inter-service requests are secured via strict `X-Service-Auth` token validation.
- **Compliance**: Adheres to 2026 Data Privacy standards and strictly processes public web information.

## 🔗 Architecture Links
- [**agent-commerce-portal**](https://github.com/SakuttoWorks/agent-commerce-portal) - Documentation Hub.
- [**agent-commerce-gateway**](https://github.com/SakuttoWorks/agent-commerce-gateway) - The Intelligent Edge (Proxy/Auth).

---
© 2026 Sakutto Works - Standardizing the Semantic Web for Agents.
