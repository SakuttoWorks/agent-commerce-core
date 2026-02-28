# Agent-Commerce-Core | The Agentic Factory
**The high-performance compute engine and deep research core for Agent-Commerce-OS.**

## 🏭 Role in Ecosystem
**Agent-Commerce-Core** is the "Factory Layer" (Layer B) of the Project GHOST SHIP infrastructure. While the [Gateway](https://github.com/SakuttoWorks/agent-commerce-gateway) handles the edge logic and billing, this core repository manages heavy-duty autonomous execution:

- **Deep Research**: Multi-step web analysis and structured data extraction.
- **RAG Engine**: Generating LLM-native Markdown/JSON optimized for retrieval.
- **Economic Reasoning**: Processing tool-use logic for autonomous commerce.

## 🛠 Tech Stack (Core Specifications)
- **Runtime**: Python 3.13+ (Optimized for async performance and GIL-free execution).
- **Framework**: FastAPI / Pydantic V2.
- **Infrastructure**: Google Cloud Run (Serverless Core).
- **Intelligence**: Integrated with Jina Reader, Firecrawl, and proprietary RAG pipelines.

## 🤖 AI-Discovery & Inter-service Logic
This core is designed to be called by the **Agent-Commerce-Gateway**.
- **Discovery**: Technical specs are synchronized via [llms.txt](https://sakutto.works/llms.txt).
- **Security**: Inter-service communication is secured via `X-Service-Auth` tokens.
- **Compliance**: Adheres to the 2026 A2A (Agent-to-Agent) standards and EU AI Act transparency requirements.

## 🔗 Architecture Links
- [**agent-commerce-portal**](https://github.com/SakuttoWorks/agent-commerce-portal) - Official Discovery Layer.
- [**agent-commerce-gateway**](https://github.com/SakuttoWorks/agent-commerce-gateway) - The Intelligent Edge (Auth/Billing).

---
© 2026 Sakutto Works - Enabling the Autonomy of Tomorrow.
