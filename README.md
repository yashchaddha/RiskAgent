# Risk Assessment Chatbot Project Documentation

## 1. Overview

This project implements an AI‑driven, conversational Risk Assessment Chatbot tailored for ISO 27001 risk registers. Built using Langraph for workflow orchestration and FastAPI for API endpoints, the system interacts with a user to generate, review, approve, and report on information‑security risks specific to an organization.

### Key Features

- **Conversational Interface**: Natural language understanding for FAQs ("What is ISO 27001?"), risk generation, editing, and approval.
- **Risk Generation**: LLM‑powered creation of draft risks following ISO 27001 controls.
- **Interactive Review**: Checkbox UI for selecting/unselecting risks, inline editing of risk attributes.
- **Metadata Collection**: Post‑approval data inputs (asset value, department, owner, target date, progress, residual exposure).
- **Persistence**: MongoDB backend for users, session state, and finalized risk registers.
- **Reporting**: On‑demand PDF/HTML report generation summarizing approved risks.

## 2. Folder Structure

```
risk_assessment_chatbot/
├── api/                   # FastAPI endpoints
├── config/                # Environment and constants
├── database/              # MongoDB connection & repositories
├── graph/                 # Langraph workflow and nodes
├── models/                # Pydantic data models
├── prompts/               # LLM prompt templates
├── services/              # Business logic layer
├── main.py                # App entrypoint
├── requirements.txt       # Dependencies
└── README.md              # Project README
```

## 3. Detailed Components

### 3.1 Configuration (`config/`)

- **settings.py**: Loads `.env` variables (Mongo URI, LLM API keys).
- **constants.py**: Constants for risk matrix values, weights, and other static data.

### 3.2 Models (`models/`)

#### `user_model.py`

- **UserModel**: Contains `id` (ObjectId) and `username`.

#### `risk_model.py`

- **RiskValueWeight**: Tuple of descriptive value and numeric weight.
- **CreatedBy**: Captures creator’s name, email, and user ID.
- **IndividualRisk**: Full risk schema as per ISO 27001 risk register sub‑document.
- **Approver**: Details for each approver (name, user reference, timestamp).
- **WeightMapping**: Defines risk matrix value/weight pairs.
- **RiskRegister**: Main document embedding individual risks and metadata.

#### `session_model.py`

- **SessionModel**: Tracks ongoing conversation state: user, current node, draft risks, selected IDs, regeneration count, metadata flag, timestamps.

### 3.3 Database (`database/`)

- **connection.py**: Initializes Motor/MongoClient connection.
- **repository.py**: CRUD operations for Users, Sessions, and RiskRegisters with upsert and optimistic locking.

### 3.4 Langraph Workflow (`graph/`)

- **workflow\.py**: Defines the Mermaid‑modeled workflow, orchestrating nodes for auth, intent parsing, knowledge, risk gen/review, metadata collection, DB persistence, and reporting.
- **nodes/**: Each node encapsulates a step:
  - **auth_node.py**: Handles user login/signup and session resume.
  - **intent_parser_node.py**: Maps text to intents.
  - **knowledge_engine_node.py**: Returns ISO 27001 educational responses.
  - **risk_generator_node.py**: Calls LLM with `prompts/risk_generation.py` to draft 10 risks.
  - **risk_reviewer_node.py**: Manages checkboxes and inline edits.
  - **metadata_collector_node.py**: Prompts for asset value, department, owner, etc.
  - **database_manager_node.py**: Saves and retrieves documents from MongoDB.
  - **report_generator_node.py**: Renders final report.
- **tools/**: Shared helpers:
  - **llm_tools.py**: Wraps LLM API calls with retry/fallback.
- **state/graph_state.py**: Defines `GraphState` holding session variables.

### 3.5 API Layer (`api/`)

- **app.py**: FastAPI instantiation, middleware, CORS.
- **routes/chat.py**: `POST /chat` endpoint forwarding messages into the Langraph agent.
- **routes/risks.py**: REST endpoints for manual risk CRUD if needed.
- **routes/reports.py**: Endpoint to fetch generated reports.

### 3.6 Prompts (`prompts/`)

- **prompts.py**: Templated system/instruction prompts guiding LLM to output properly.

### 3.7 Services (`services/`)

- **user_service.py**: Business logic for user lookup, creation, and session management.
- **risk_service.py**: Core operations to generate, validate, and transform risk drafts.
- **report_service.py**: Builds the final PDF/HTML report, aggregates metrics.

### 3.9 Example Generated Risks

Below is the sample table of 10 draft risks the agent initially generates for the user (all checkboxes are checked by default):

| Risk ID | Risk Description                                                                                          | Likelihood | Impact    | Treatment Strategy | Treatment Measures                                                                                   |
| ------- | --------------------------------------------------------------------------------------------------------- | ---------- | --------- | ------------------ | ---------------------------------------------------------------------------------------------------- |
| R-001   | Unauthorized physical access to production servers or network closets                                     | Medium     | High      | Mitigate           | Install badge readers and CCTV; maintain visitor logs and escorts.                                   |
| R-002   | Theft or loss of mobile devices containing sensitive design/specification files                           | High       | Medium    | Mitigate           | Enforce disk encryption; enable remote-wipe; train staff on device security.                         |
| R-003   | Malware infection via USB drives or external media                                                        | Medium     | High      | Mitigate           | Disable autorun; deploy real-time anti-malware; enforce media scanning policy.                       |
| R-004   | Phishing attacks leading to credential compromise                                                         | High       | High      | Mitigate           | Conduct phishing simulations; implement MFA; run awareness campaigns.                                |
| R-005   | Ransomware encrypting production data and demanding payment                                               | Medium     | Very High | Mitigate           | Maintain offline backups; patch systems promptly; segment network.                                   |
| R-006   | Insider threat: improper disclosure or sabotage of proprietary manufacturing processes                    | Low        | Very High | Mitigate/Accept    | Enforce least-privilege; user-activity logging; confidentiality clauses in contracts.                |
| R-007   | Supplier service-outage or data breach at critical third-party IT vendor                                  | Medium     | High      | Transfer/Mitigate  | Require ISO 27001 certification; include SLAs and breach-notification clauses; review audit reports. |
| R-008   | Unpatched vulnerabilities in SCADA or industrial-control systems                                          | Medium     | Very High | Mitigate           | Maintain ICS inventory; dedicated patch process; segment OT from corporate networks.                 |
| R-009   | Unintentional data disclosure via misconfigured file-share permissions                                    | High       | Medium    | Mitigate           | Implement RBAC; deploy DLP tools; train users on classification and access controls.                 |
| R-010   | Business-disrupting natural disasters (typhoons, floods) damaging primary data-center or plant IT systems | Low        | Very High | Transfer/Mitigate  | Establish off-site DR site; maintain UPS/generators; rehearse disaster recovery procedures.          |

## 4. Detailed User Flow

Below is a step-by-step conversational journey illustrating how the agent interacts with a user:

1. **Greeting & Authentication**

   - **Agent**: “Hello! Welcome to the ISO 27001 Risk Assessment Bot. Please enter your username to continue.”
   - **User**: Enters username (e.g., `jdoe`).
     - If username exists: **Agent** “Welcome back, [First Name]! Resuming your session…”
     - If not: **Agent** “I don’t recognize that username. Would you like to create a new account?”
       - **User**: Confirms → **Agent**: “Great! What’s your first and last name and email?” → Account is created → proceed to intent parsing.

2. **FAQ & Educational Queries**

   - At any point, **User** can ask: “What is ISO 27001?”, “How are risks determined?”, or “What is a risk register?”
   - **Agent** routes to the KnowledgeEngine node, provides concise definitions, then asks “Would you like to resume where we left off?”

3. **Risk Generation**

   - **User**: “Generate risks for my organization.”
   - **Agent**: Uses hardcoded organization context (e.g., “Philippine Manufacturing Co.”) and calls the RiskGenerator node to produce 10 draft risks via the LLM.
   - **Agent**: Validates schema, saves draft in session model, then displays a checklist of 10 risks (all checked by default).

4. **Review & Editing**

   - **User** toggles checkboxes to deselect unwanted risks.
   - **User**: “Change likelihood of R-003 to High.” → **Agent**: Validates Risk ID exists, updates session state, and confirms the update.
   - **User**: “Add more risks.” → **Agent**: Checks regeneration count, warns if limit reached, then calls RiskGenerator again.

5. **Finalize Selection & Approval**

   - **User**: Clicks “Finalize Selection.”
   - **Agent**: If no risks selected, warns and returns to review. Otherwise, asks “Confirm final approval of X risks?”
   - **User**: Confirms → **Agent** saves an approval checkpoint and transitions to metadata collection.

6. **Metadata Collection**

   - **Agent**: Presents form or conversational prompts to collect for each approved risk:
     - Asset Value (numeric)
     - Department (pick from predefined list)
     - Risk Owner (name or role)
     - Target Date (YYYY-MM-DD)
     - Risk Progress (Not started / In progress / Complete)
     - Residual Exposure (value + weight)
   - **Agent**: Validates each input; on errors, requests correction.

7. **Save & Report Generation**

   - **Agent**: “All set! Would you like to save your register and generate the report now?”
   - **User**: Confirms → **Agent** writes the `RiskRegister` document to MongoDB (with optimistic locking).
   - On save success: **Agent** invokes the ReportGenerator node to produce a PDF/HTML report and returns a view or link.
   - On save failure: **Agent** offers retry options (retry now, retry later, contact support) and persists session state if deferred.

8. **Session Management & Exit**

   - **Agent**: Auto-saves session after each checkpoint.
   - **User**: Can type “exit” at any time; **Agent** responds “Your progress is saved. See you next time!” and ends the session.
