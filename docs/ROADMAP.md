# Roadmap

This roadmap outlines **planned, production-oriented improvements** to the project. The focus is on scalability, cost control, and correct system design rather than adding features and unnecessary complexity.

Only **Phase 1** and **Phase 2** are guaranteed to be implemented. **Phase 3** represents optional extensions that may be partially implemented or documented, depending on time.

---

## Phase 1 — Daily Meal Batching (Planned)

**Goal:** Reduce LLM usage and improve system efficiency.

### What will be done
- Generate a full daily meal plan for each user in a single background job
- Persist the daily plan in PostgreSQL
- Serve meal suggestions at scheduled times from stored data instead of recomputing

### Why
- Significantly reduces expensive LLM calls
- Matches real-world batch processing patterns
- Improves predictability and observability

### Key Concepts
- Batch processing
- Cost-aware system design
- Background job orchestration

---

## Phase 2 — Server-Sent Events (SSE) for Updates (Planned)

**Goal:** Simplify real-time communication between backend and frontend.

### What will be done
- Replace WebSockets with Server-Sent Events (SSE)
- Use SSE for one-way updates such as:
  - Meal plan readiness
  - Inventory changes after background tasks

### Why
- SSE is a better fit for one-directional server updates
- Simpler to reason about and scale than WebSockets
- Demonstrates correct transport selection rather than over-engineering

### Key Concepts
- Event-driven systems
- Real-time backend communication
- Practical protocol choice

---

## Phase 3 — Retrieval, AI Optimization & Hardening (Optional)

This phase combines several enhancements that further reduce AI usage and improve robustness. These may be implemented partially or documented depending on scope.

### Possible Enhancements
- Vector database for recipe retrieval (semantic search over a recipe corpus)
- Semantic caching of meal ideas to reuse suggestions across users
- Rule-based ingredient classification (prepared foods, fruits, staples, recipe-only)
- LLM usage restricted to explicit user-driven actions (e.g., prioritized ingredients)
- Rate limiting on AI-powered endpoints
- Language normalization between retrieved and generated meals

### Why
- Demonstrates modern RAG-style system design
- Shows understanding of when **not** to use LLMs
- Improves scalability and cost predictability


