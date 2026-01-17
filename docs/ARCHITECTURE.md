# System Architecture

```mermaid
graph LR
    %% -- Entities --
    User((fa:fa-user User))
    
    subgraph Client_Layer [Frontend Layer]
        NextJS[fa:fa-react Next.js / Vercel]
    end

    subgraph AWS_Infrastructure [AWS Cloud Environment]
        subgraph Compute_EC2 [EC2 Instance: Dockerized Stack]
            Nginx{fa:fa-server Nginx Proxy}
            
            subgraph Backend_Services [App Layer]
                API[fa:fa-bolt FastAPI API]
                Beat[fa:fa-clock Celery Beat]
                Worker[fa:fa-robot Celery Worker]
            end

            subgraph Message_Broker [State & Queue]
                Redis[(fa:fa-layer-group Redis)]
            end
        end

        subgraph Data_Storage [Persistence]
            RDS[(fa:fa-database AWS RDS Postgres)]
        end
    end

    subgraph External AI Services
        LLM[fa:fa-brain LLM Provider]
    end

    %% -- Data Flows --
    User -- HTTPS/WSS --> NextJS
    NextJS -- REST/JSON --> Nginx
    NextJS -- Real-time Streams --> Nginx
    Nginx -- Proxy --> API

    %% Sync Paths
    API -- SQL Query --> RDS
    
    %% Async Paths
    API -- Task Producer --> Redis
    Beat -- Cron Trigger --> Redis
    Redis -- Task Consumer --> Worker
    
    %% AI Inference
    Worker -- Contextual Prompt --> LLM
    LLM -- Structured Recipe --> Worker
    
    %% Feedback Loop
    Worker -- Write Results --> RDS
    Worker -- Status Event --> Redis
    Redis -- Pub/Sub Update --> API
    API -- WebSocket Push --> NextJS

    %% Styling
    %% User override to make it stand out
    style User fill:#FFF9C4,stroke:#FBC02D,stroke-width:2px,color:#333

    %% Define professional classes
    %% Containers: Neutral grays to fade into background
    classDef container fill:#F5F7FA,stroke:#B0BEC5,stroke-width:1px,stroke-dasharray: 5 5,color:#37474F;

    %% Compute Services (API, Frontend, Workers): Clean professional blue
    classDef service fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#0D47A1;

    %% Data/State (Databases, Redis): Stable Indigo/Purple
    classDef database fill:#EDE7F6,stroke:#5E35B1,stroke-width:2px,color:#311B92;

    %% External AI: Distinct Teal accent
    classDef ai fill:#E0F7FA,stroke:#00BCD4,stroke-width:2px,color:#006064;

    %% Apply Classes
    class AWS_Infrastructure,Client_Layer,Compute_EC2,Backend_Services,Message_Broker,Data_Storage,Intelligence_Layer container;
    class NextJS,Nginx,API,Beat,Worker service;
    class RDS,Redis database;
    class LLM ai;