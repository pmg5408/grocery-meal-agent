# System Architecture

This document outlines the high-level architecture of the **Grocery & Meal Agent** platform. The system is designed as a cloud-native, event-driven application that separates user interaction (Frontend) from heavy computational tasks (AI Agents).

## High-Level Diagram

The system assumes a **hybrid cloud deployment**:
* **Frontend:** Hosted on Vercel (Edge Network).
* **Backend Ecosystem:** Containerized services hosted on AWS EC2.
* **Data Persistence:** Managed AWS RDS.

```mermaid
graph TD
    %% -- User Layer --
    User((User / Browser))
    
    %% -- Vercel / Frontend --
    subgraph Vercel_Cloud [Vercel Deployment]
        NextJS[Next.js Frontend]
    end

    %% -- AWS Infrastructure --
    subgraph AWS_Cloud [AWS Cloud Environment]
        
        %% -- Database --
        RDS[(AWS RDS Postgres)]

        %% -- EC2 Instance --
        subgraph EC2_Instance [EC2 Instance t2.micro]
            Nginx[Nginx Reverse Proxy]
            
            %% -- Docker Network --
            subgraph Docker_Network [Docker Swarm / Compose]
                API[FastAPI Backend]
                Redis[(Redis Broker)]
                Worker[Celery Worker Agent]
                Beat[Celery Beat Scheduler]
            end
        end
    end

    %% -- External Services --
    subgraph External_AI [External AI Providers]
        LLM[OpenAI / Gemini API]
    end

    %% -- Connections --
    User -- HTTPS --> NextJS
    NextJS -- HTTPS / WSS --> Nginx
    Nginx -- Reverse Proxy --> API
    
    %% Backend Logic
    API -- Read/Write --> RDS
    API -- Enqueue Task --> Redis
    
    %% Async Workflow
    Beat -- Schedule Crons --> Redis
    Redis -- Consume Task --> Worker
    Worker -- Inference Request --> LLM
    Worker -- Save Results --> RDS
    Worker -- Pub/Sub Updates --> Redis
    
    %% Realtime Feedback
    Redis -- Update Event --> API
    API -- WebSocket Push --> NextJS
    
    %% Styling
    style User fill:#f9f,stroke:#333,stroke-width:2px
    style RDS fill:#316192,stroke:#fff,stroke-width:2px,color:#fff
    style Redis fill:#DD0031,stroke:#fff,stroke-width:2px,color:#fff
    style LLM fill:#10a37f,stroke:#fff,stroke-width:2px,color:#fff
    style Worker fill:#ff9900,stroke:#333,stroke-width:2px