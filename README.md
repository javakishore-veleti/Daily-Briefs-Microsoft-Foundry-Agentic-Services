# Daily Briefs — Microsoft Foundry Agentic Services

Enterprise Briefs is a local Angular portal plus Python middleware that talks to **Microsoft Foundry** agents. Each menu item is one brief. The portal sends the user’s question; middleware calls Foundry; the reply shown is the agent’s text.

| Brief | Portal route | What it does |
| --- | --- | --- |
| Daily Briefs Search | `/daily-briefs-search` | Searches the web, then answers briefly |
| Weather Agent | `/weather-agent` | Calls a weather OpenAPI tool (wttr.in), then answers |
| HR Daily Brief | `/hr-daily-brief` | Lists joiners from MongoDB, then asks an HR agent about one joiner using Foundry Memory |

Default local URLs: portal `http://127.0.0.1:4200`, middleware `http://127.0.0.1:8000` (Swagger `/docs`).

---

## Purpose of each brief (AI-focused)

### 1. Daily Briefs Search

- **Job:** Answer general questions with live web results.
- **Foundry agent:** `web-search-agent`
- **AI capability:** Built-in Foundry **web search** tool. The model searches, then writes a short answer.
- **Middleware:** Passes the user question to `responses.create` with `agent_reference` for that agent. Returns `output_text` unchanged.
- **API:** `POST /api/v1/daily-briefs/web-search`

### 2. Weather Agent

- **Job:** Answer weather questions for a place, including follow-ups in the same chat.
- **Foundry agent:** `weather-agent`
- **AI capability:** **OpenAPI tool** named `weather` (`GetCurrentWeather`) against `https://wttr.in/{location}?format=j1`. The model must call the tool; Foundry runs the HTTP call; the model summarizes the JSON.
- **Model note:** The OpenAPI weather tool works with models Foundry allows for that tool (for example `gpt-4o` / `gpt-4.1`). Some models (for example `gpt-5-mini`) may refuse the tool and only narrate.
- **Middleware:** Pass-through of agent `output_text`. No place parsing and no local forecast rewrite.
- **API:** `POST /api/v1/daily-briefs/weather-info`

### 3. HR Daily Brief

- **Job:** Help HR look at **new joiners** and ask preference questions about one joiner.
- **Foundry agent:** `hr-assistant-agent` (no tools on the agent definition)
- **AI capability:** **Foundry Memory Store** `hr-joiner-memory` with chat model + embedding model. Per-joiner isolation uses `scope = joiner_info_id`. Middleware:
  1. Writes joiner preferences from Mongo into memory (`begin_update_memories`)
  2. Searches memory for the question (`search_memories`)
  3. Sends joiner record + optional “Memory context” + question to the agent
  4. Shows the agent reply unchanged
- **Portal flow:** List joiners by joining date (10 per page) → open one joiner → see **Joiner info** and **Joiner preferences** → chat (history keyed by `joiner_info_id`)
- **APIs:** `GET /api/v1/daily-briefs/joiners`, `GET /api/v1/daily-briefs/joiners/{id}`, `POST /api/v1/daily-briefs/hr-assistant`

The left-hand joiner card is **MongoDB**. Preference answers from the agent come from **Foundry Memory**, not from reading that card on every reply. If memory search/update fails (for example Azure OpenAI **401** on the embedding deployment), the agent correctly says it has no memory yet.

---

## System design

```text
Angular portal (Enterprise Briefs)
        │  HTTP
        ▼
FastAPI  /api/v1/daily-briefs/*
        │
        ▼
Facades  →  Tasks  →  Adapters (Foundry) + DAOs (Mongo)
                        │                    │
                        ▼                    ▼
              Microsoft Foundry         MongoDB collections
              agents + memory           chatuser, chatsession,
                                        chathistory, joiner-info,
                                        joiner-preferences
```

| Layer | Role |
| --- | --- |
| Portal | Sign-in, brief menus, chat UI, HR joiner list/detail |
| API | Thin HTTP → facade |
| Facade / tasks | Orchestration and recording chat history |
| Adapter | Foundry `responses.create`, agent ensure, memory search/update |
| DAO | Mongo entity managers |

**Startup order:** DAO init → Foundry adapters (ensure agents + HR memory store) → facades.

**Conversation continuity:** Portal `session_id` maps to one Foundry `conversation_id` (in-memory `SessionCache`). **New chat** starts a new session UUID. Restarting middleware clears the cache; Mongo chat history remains.

**Chat history:** One prompt document and many response documents per turn. HR chats set `joiner_info_id` on those documents.

---

## Azure services used

| Azure / external piece | Used for |
| --- | --- |
| Microsoft Foundry **project** | Host for agents and memory (`FOUNDRY_PROJECT_ENDPOINT`) |
| Foundry **Agents** | `web-search-agent`, `weather-agent`, `hr-assistant-agent` |
| Foundry **Memory** | `hr-joiner-memory` (user profile + chat summary features) |
| Model **deployments** | Chat: `MODEL_DEPLOYMENT_NAME` (for example `gpt-4.1`). Embeddings: `TEXT_EMBEDDING_MODEL_NAME` (for example `text-embedding-3-small`) |
| Built-in **web search** | Daily Briefs Search |
| **OpenAPI** tool → wttr.in | Weather Agent |
| Project **managed identity** + RBAC | Memory store calls chat/embedding deployments inside Foundry |

Auth to Foundry from this app: project endpoint + `FOUNDRY_API_KEY` (and `DefaultAzureCredential` where the SDK uses it). Do not commit `.env`.

**RBAC that memory needs (portal or Actions):** On the Foundry **account** that contains the project, the **project managed identity** needs permission to call model deployments (docs: **Foundry User**; if memory still returns AOAI **401**, also assign **Cognitive Services OpenAI User** to that same project identity). Foundry User already present does not always unlock memory embeddings by itself.

---

## MongoDB (local)

| Collection | Purpose |
| --- | --- |
| `chatuser` | Portal accounts (default seed: `enterprise-user` / `password`) |
| `chatsession` | Chat sessions |
| `chathistory` | Prompts and agent replies (`joiner_info_id` for HR) |
| `joiner-info` | New joiner master record + `joining_date` |
| `joiner-preferences` | Resumes, personal interests, food preferences (FK → joiner-info) |

Empty `joiner-info` is seeded with sample joiners on DAO init so the HR list is usable.

---

## How to run locally

1. Copy values into `.env` (gitignored): `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_API_KEY`, `MODEL_DEPLOYMENT_NAME`, `TEXT_EMBEDDING_MODEL_NAME`, Mongo settings.
2. Start Mongo:

```bash
npm run local:containers:start-all
```

3. Start middleware and portal:

```bash
npm run local:run-all
# or separately:
npm run local:middleware:start
npm run local:portals:start
```

4. Open `http://127.0.0.1:4200`, sign in as `enterprise-user` / `password`.

Useful scripts: `local:stop-all`, `local:status-all`, `local:containers:stop-all` (stop-all for containers uses `docker compose down --volumes` and **wipes** Mongo data).

---

## How to use each brief

### Daily Briefs Search / Weather Agent

1. Open the menu item.
2. Ask a question; wait for the reply.
3. Use **New chat** when you want a fresh Foundry conversation (new agent behavior or a new place for weather).

### HR Daily Brief

1. Open **HR Daily Brief**.
2. Pick a joining date; open a joiner.
3. Confirm preferences on the card (Mongo).
4. Ask in chat (for example food preferences). First successful memory update stores the profile; a later question in a **new chat** should recall it once memory auth works.
5. Chat history stays on that joiner.

---

## GitHub Actions (Azure setup)

Agents and the HR memory store can be created from GitHub with **workflow_dispatch**. Create workflows ask for confirmation:

> **Agent Created Already In Code, Do You Still Run This Github Action?** → default **`no`**. Choose **`yes`** only when you intend to publish in Azure from CI.

Middleware startup also ensures agents and the memory store when the app starts, so Actions are optional if you run middleware with a valid `.env`.

| Workflow | Creates / updates | Confirmation |
| --- | --- | --- |
| `AzureFoundry-001-Agent-WebSearch-Create.yml` | `web-search-agent` | `still_run` default `no` |
| `AzureFoundry-002-Agent-WebSearch-Delete.yml` | Deletes `web-search-agent` | None (always runs) |
| `AzureFoundry-003-Agent-HRAssistant-Create.yml` | `hr-assistant-agent` | `still_run` default `no` |
| `AzureFoundry-004-Agent-Weather-Create.yml` | `weather-agent` + OpenAPI weather tool | `still_run` default `no` |
| `AzureFoundry-005-MemoryStore-HRJoiner-Create.yml` | Memory store `hr-joiner-memory` | `still_run` default `no` |
| `AzureFoundry-006-Memory-RBAC-Assign.yml` | Assigns Foundry User + Cognitive Services OpenAI User to the **project** managed identity on the Foundry account | `still_run` default `no` |

**Repository secrets**

| Secret | Used by |
| --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | Agent + memory workflows (001–005) |
| `FOUNDRY_API_KEY` | Agent + memory workflows (001–005) |
| `AZURE_CREDENTIALS` | 006 only — Azure service principal JSON for `azure/login` |
| `FOUNDRY_ACCOUNT_RESOURCE_ID` | 006 — ARM id of the Foundry / AI Services account |
| `FOUNDRY_PROJECT_PRINCIPAL_ID` | 006 — Object (principal) id of the **project** managed identity |

What Actions **do not** replace: deploying models in Foundry, creating the Foundry project itself, or fixing a bad API key. Memory still needs the RBAC in 006 (or the same roles in the Azure portal) before preference search works.

---

## Environment variables (middleware)

| Variable | Meaning |
| --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | Project URL `…/api/projects/{name}` |
| `FOUNDRY_API_KEY` | Project API key |
| `MODEL_DEPLOYMENT_NAME` | Chat deployment used by agents / memory chat model |
| `TEXT_EMBEDDING_MODEL_NAME` | Embedding deployment for the HR memory store |
| `REASONING_EFFORT` | Used for gpt-5* agent definitions when published |
| `HR_MEMORY_STORE_NAME` | Default `hr-joiner-memory` |
| `HR_MEMORY_PROFILE_DETAILS` | Default food preferences, personal interests, resumes |
| `DB_TECHNOLOGY` | `mongodb` (local default) |
| `MONGODB_URI` / `MONGODB_DATABASE` | Local Docker defaults |

---

## Repo layout (short)

```text
middleware/          FastAPI, facades, Foundry adapters, Mongo DAOs
portals/enterprise-briefs/   Angular portal
.github/workflows/   Foundry agent / memory / RBAC Actions
DevOps/Local/        Mongo docker compose helpers
scripts/             local middleware / portal start-stop
```
