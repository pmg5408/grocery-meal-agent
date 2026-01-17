# Tradeoffs and Decisions

This document highlights a small set of architectural decisions that meaningfully shaped the system.
The focus is on choices made for learning, simplicity, and iteration speed rather than exhaustive evaluation
of all possible alternatives.

---

## Backend Framework: FastAPI

**Rationale**
- FastAPI was chosen primarily as a learning-driven decision.
- I wanted hands-on experience with a modern, async-first Python framework.
- Strong typing and automatic OpenAPI generation helped accelerate development and improve correctness.

**Tradeoffs**
- Fewer built-in abstractions compared to Django.
- Requires more explicit architectural decisions as the application grows.

---

## Background Processing & Scheduling

**Decision**  
Asynchronous work is handled using Celery, with Celery Beat running a periodic scheduler.

**Rationale**
- Certain workflows (e.g., meal generation) are time-based and potentially long-running.
- A periodic scheduler that scans database-backed triggers was simpler than maintaining per-user cron jobs.
- This model keeps scheduling logic centralized and application-aware.
- This model may evolve toward event- or time-slot–driven scheduling to reduce unnecessary scans.

**Tradeoffs**
- Requires always-on worker and scheduler processes.
- Periodic polling introduces minor inefficiency at scale but simplified early iteration and observability.

---

## Real-Time Client Updates

**Decision**  
WebSockets are currently used to notify clients when asynchronous tasks (e.g., meal generation) complete.

**Rationale**
- WebSockets were initially chosen as a straightforward way to push real-time updates from the backend to the client.
- They provided a simple mental model during early development.

**Tradeoffs**
- Bidirectional communication is not strictly required for this use case.
- Maintaining WebSocket connections introduces additional operational complexity.

**Notes**
- As the system evolved, it became clear that Server-Sent Events (SSE) may be a better fit for one-way,
  event-driven updates. This is documented as a potential improvement in the project roadmap.

---

## Scope and Intent

Many foundational technology choices (e.g., database, containerization) were treated as reasonable defaults and are intentionally omitted to keep this document focused on decisions with the highest architectural impact.

This project emphasizes:
- Learning through implementation
- Shipping end-to-end functionality
- Iterating based on observed constraints rather than theoretical optimization
