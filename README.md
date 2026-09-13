# Kindly

> **An AI-powered web agent that turns natural-language brain dumps into a schedule for real-world tasks.**

Kindly is an AI-powered personal planning agent built to reduce the friction of everyday online tasks. Instead of simply generating recommendations or instructions, Kindly interprets a user's intent, decomposes it into actionable tasks, schedules those tasks around existing commitments, and uses web agents to retrieve relevant real-world information.

---

## What We Built

A user can give Kindly an unstructured request such as:

```text
"I have class at 2, I need to study afterwards,
and I want to find somewhere to eat for dinner."
```

Kindly transforms this into structured data, determines which events are fixed versus flexible, computes a conflict-free schedule, researches only the services or locations that actually require research, and returns a unified plan.

The core architecture separates **LLM-based reasoning** from **deterministic computation**.

```text
Natural Language –> Gemini Natural Language Parsing –> Structured Task Representation –> Python Scheduler Determines Time Allocation
–> Steel.dev Web Agent OR Fixed Events & Constraits –> Gemini Final Output –> Kindly UI
```

---

# System Architecture

Kindly uses a multi-stage pipeline rather than asking an LLM to perform the entire workflow.

### 1. Natural-Language Intent Extraction

Gemini acts as the natural-language interface.

The model converts unstructured user input into structured task objects containing information such as:

```python
{
    "task": "Math class",
    "fixed_time": "2 PM",
    "duration_minutes": 60
}
```

or:

```python
{
    "task": "Study for CSC test",
    "duration_minutes": 90
}
```

This allows the rest of the system to operate on structured data instead of raw natural language.

---

# FastAPI Backend

Kindly uses **FastAPI** as its backend framework.

FastAPI provides the HTTP API layer connecting the frontend to the AI, scheduling engine, and web-agent infrastructure.

Conceptually:

```text
Frontend
   │
   │ HTTP Request
   ▼
FastAPI
   │
   ├──► Gemini
   │
   ├──► Scheduler
   │
   └──► Steel.dev
            │
            ▼
       Web Research
```

FastAPI was chosen because it provides a lightweight, asynchronous Python backend with clean API routing and strong support for structured request/response models.

The backend is responsible for:

* Receiving user requests
* Validating input
* Calling the LLM
* Running scheduling logic
* Orchestrating web-agent tasks
* Combining results
* Returning structured responses to the frontend

This keeps the frontend decoupled from the underlying AI and agent infrastructure.

---

# LLM + Deterministic Scheduling

One of the most important architectural decisions in Kindly is that **the LLM does not control the final schedule**.

Gemini is responsible for understanding the user's intent.

Python is responsible for calculating the schedule.

This separation prevents common LLM failure modes such as:

* Inventing times
* Creating overlapping events
* Moving fixed commitments
* Reordering tasks unnecessarily
* Ignoring time constraints

The scheduler deterministically enforces:

* Fixed events
* Flexible tasks
* User availability
* Task durations
* 10-minute transition buffers
* Meal scheduling windows
* Conflict detection
* End-of-day constraints

For example:

```text
9:00 AM  ─ Study
10:30 AM ─ 10-minute transition
10:40 AM ─ Assignment
2:00 PM  ─ Math class (FIXED)
3:00 PM  ─ Study
5:30 PM  ─ Dinner
```

The LLM can interpret the request, but the Python scheduling engine determines whether those time allocations are actually valid.

---

# Steel.dev Web Agent

Kindly uses **Steel.dev** as part of its web-agent infrastructure.

Steel provides browser infrastructure that allows Kindly to interact with the web and retrieve real-world information instead of relying entirely on static LLM knowledge.

This is particularly important for tasks where information can change dynamically.

For example:

```text
"Find me a quiet place to study."
```

requires real-world information.

Kindly can use its web-agent layer to research relevant locations and gather information that can be presented to the user.

---

## Selective Web Research

Kindly does **not** send every task to the web agent.

The system first determines whether the user actually needs external information.

For example:

```text
"I have math class at 2."
```

does not require web research.

```text
"I need somewhere quiet to study."
```

does require web research.

```text
"I have a dentist appointment at 3."
```

does not require researching the dentist.

```text
"Find me a dentist appointment at 3."
```

does require web research.

This reduces unnecessary agent calls and makes the system more efficient.

---

# Agent Orchestration

The backend effectively acts as an orchestration layer between multiple specialized components.

```text
                 ┌───────────────┐
                 │    Gemini     │
                 │  NLP / Intent │
                 └───────┬───────┘
                         │
                         ▼
                Structured Tasks
                         │
                         ▼
                 ┌───────────────┐
                 │ Python Engine │
                 │  Scheduling   │
                 └───────┬───────┘
                         │
                ┌────────┴────────┐
                ▼                 ▼
        Fixed Constraints     Research Tasks
                                  │
                                  ▼
                           ┌─────────────┐
                           │  Steel.dev  │
                           │ Web Agent   │
                           └──────┬──────┘
                                  │
                                  ▼
                           Web Information
                                  │
                                  ▼
                           ┌─────────────┐
                           │   Gemini    │
                           │  Synthesis  │
                           └─────────────┘
```

This architecture allows each component to specialize in what it does best.

---

# Constraint-Based Scheduling

The scheduling engine treats the user's day as a constrained time-allocation problem.

### Hard Constraints

These cannot be violated:

* Fixed event times
* User's start time
* User's end time
* Task durations
* No overlapping events

### Soft Constraints

These are preferences that the scheduler tries to satisfy:

* Lunch around 11:30 AM–1:30 PM
* Dinner around 5:30 PM–7:30 PM
* 10-minute transition periods
* Preserving the user's original task order

This gives the scheduler predictable behavior while still producing a natural-looking day.

---

# Data Flow

A simplified request lifecycle looks like:

```text
1. User submits request
          ↓
2. FastAPI receives HTTP request
          ↓
3. Gemini extracts structured intent
          ↓
4. Backend separates fixed/flexible tasks
          ↓
5. Python scheduler calculates valid times
          ↓
6. Research tasks are sent to web-agent layer
          ↓
7. Steel.dev retrieves real-world information
          ↓
8. Gemini synthesizes the results
          ↓
9. FastAPI returns structured response
          ↓
10. Frontend renders the final plan
```

---

# 🛠️ Tech Stack

| Technology              | Role                                                  |
| ----------------------- | ----------------------------------------------------- |
| **Python**              | Core backend logic and scheduling engine              |
| **FastAPI**             | REST API / backend service                            |
| **Gemini**              | Natural-language understanding and response synthesis |
| **Steel.dev**           | Browser infrastructure and web-agent capabilities     |
| **HTML/CSS/JavaScript** | Frontend                                              |
| **asyncio**             | Asynchronous backend operations                       |
| **python-dotenv**       | Environment configuration                             |

---

# Backend Responsibilities

The FastAPI backend acts as the central orchestration layer.

It handles:

```text
HTTP Requests
      ↓
Input Validation
      ↓
LLM Processing
      ↓
Task Structuring
      ↓
Scheduling
      ↓
Web-Agent Calls
      ↓
Result Aggregation
      ↓
JSON Response
```

This allows the frontend to remain relatively lightweight while the backend handles the computational and agentic workflow.

---

# Environment Variables

API keys are stored outside the source code using environment variables.

Example:

```env
GEMINI_API_KEY=your_api_key
STEEL_API_KEY=your_api_key
```

Secrets are excluded from version control using `.gitignore`.

```gitignore
.env
venv/
__pycache__/
*.pyc
```

---

# Running Locally

### Clone the repository

```bash
git clone YOUR_REPOSITORY_URL
cd YOUR_REPOSITORY_FOLDER
```

### Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key
STEEL_API_KEY=your_api_key
```

### Start the FastAPI server

```bash
uvicorn main:app --reload
```

The application will then be available through the local development server.

---

# Reliability & Validation

A major design goal is preventing the AI layer from silently producing invalid schedules.

The Python scheduler performs validation after scheduling.

It checks for:

* Time conflicts
* Invalid task placement
* Tasks exceeding the available window
* Fixed-event collisions
* Tasks that could not be scheduled

If a task cannot fit, the system marks it as:

```python
"status": "needs_rescheduling"
```

rather than pretending that the task was successfully scheduled.

---

# Why This Architecture?

Many AI applications ask an LLM to perform the entire workflow.

Kindly instead uses a **hybrid architecture**:

```text
LLM
→ probabilistic reasoning
→ natural-language understanding

Python
→ deterministic computation
→ constraint enforcement

Steel.dev
→ browser infrastructure
→ real-world web interaction

FastAPI
→ service orchestration
→ API communication
```

This gives Kindly the flexibility of an AI agent while maintaining deterministic control over critical operations such as scheduling.

---

# Our Technical Approach

Kindly is built around one core idea:

> **Use AI where ambiguity exists, and deterministic software where correctness matters.**

Gemini understands what the user means.

Python determines what can actually fit.

Steel.dev connects the system to the real world.

FastAPI coordinates the entire pipeline.

The result is an agent that doesn't just **tell users what to do** — it helps turn their intentions into an executable plan.

---

# Future Work

Potential extensions include:

* Calendar API integration
* Automated appointment booking
* Transit-aware scheduling
* Persistent user preferences
* Multi-day planning
* Automatic rescheduling
* Voice interfaces
* Notification and reminder systems
* More sophisticated constraint optimization
* Parallelized web-agent workflows
* Personalized scheduling models

---

Built with ❤️ by Team Caramel (Mika & Susie)

**Kindly — because getting things done should be easier than figuring out how to do them.**
