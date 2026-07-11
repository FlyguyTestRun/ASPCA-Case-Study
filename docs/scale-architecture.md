# Scale Architecture: What Gets Built, and What Triggers It

This system is deliberately small. At 50 donors, the correct architecture is a deterministic pipeline, a schema, a review gate, and a folder of files, and every component beyond that would be bloat wearing a best-practice costume. Knowing when not to use an LLM extends to knowing when not to use infrastructure.

But small on purpose is different from small by ignorance. Each component below is deliberately absent, with the specific condition that would justify building it. This is the build order I would defend in an architecture review.

| Component | Deliberately absent because | Build it when |
|-----------|------------------------------|---------------|
| **CRM connector** (replacing file upload) | The exercise supplies a file; a connector needs a real CRM and its access model | The donor source of truth is a live system. First priority at any real deployment: joins move to donor IDs, the exceptions report starts feeding corrections back upstream, and the upload path retires along with its security risks |
| **Database instead of CSV artifacts** | Files are auditable, diffable, and sufficient at this volume | Concurrent campaigns, multiple reviewers, or history queries ("what did we send this donor last year") appear. The run artifacts are already structured, so this is a storage swap, not a redesign |
| **Batch queue and job orchestration** | Three scripts in sequence complete in seconds | Runs take minutes, overlap, or need retry semantics. The stages are already separate processes with file interfaces, which is exactly the shape a queue consumes |
| **Semantic caching** | This is a batch pipeline; nothing asks the same question twice | An interactive surface exists (staff querying donor data conversationally). Cache by data volatility: giving history is stable, campaign status is not |
| **Model tiering and token budgets** | The batch path uses zero tokens; the optional personalization step is bounded per letter | Model-written personalization runs at volume. Then: a small model for routine paragraphs, a frontier model for flagged cases, per-campaign token budgets enforced at the gateway, acceptance thresholds tied to the confidence rubric |
| **MCP servers** | One skill reading local files needs no protocol layer | Multiple agents or assistants need governed access to the same donor tools. MCP is the boundary where tool access gets authenticated, logged, and rate-limited instead of copied into every agent |
| **Containers and deployment infrastructure** | A reviewer can run this with Python and one pip install; that accessibility is a feature of a case study | The review app serves a team instead of a laptop. Containerize the pipeline and app together so the versions that reviewed a batch are pinned and reproducible |
| **RAG / knowledge retrieval** | The letters' language comes from an approved library on purpose; retrieval would add variance where governance wants none | The system starts answering open questions (donor histories, policy lookups, campaign research) rather than filling governed templates |
| **Orchestration frameworks** (LangGraph and similar) | A linear three-stage pipeline does not need a graph engine | The workflow gains real branches: multi-step approvals, parallel campaign runs, human-in-the-loop resumption across days. Durable checkpointed state is the signal that hand-rolled sequencing has hit its ceiling |
| **IAM and per-user audit** | A local demo cannot honestly implement enterprise identity; pretending would be theater | The app is deployed for a team. Then every correction approval and style adoption records who, via the organization's identity provider, and the approval fields already in the data model get real identities behind them |
| **Evaluation service and letter-quality evals** | 81 deterministic tests cover a deterministic system | A model writes personalization at scale. Reviewer edits versus drafts become a measured quality series; regression evals gate model or prompt changes the way the trap suite gates logic changes today |

Two principles govern the whole table:

1. **Triggers, not fashion.** Every row names the observable condition that changes the answer. Absent the trigger, the component is cost and attack surface with no compensating value.
2. **The spine never changes.** Validate, compute, gate, render, review. Every scale component attaches to that spine at a defined interface (the validator boundary, the escalation stream, the letter model schema) rather than replacing it. That is what it means for the durable IP to live in the data and the policy instead of the model.
