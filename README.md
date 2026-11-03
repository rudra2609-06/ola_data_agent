# SQL Analyst Agent (ola_data_agent)

An agentic workflow that turns a plain-English question into a safe PostgreSQL query, runs it, and returns a short, readable answer. Built with LangGraph, PostgreSQL and an LLM-based safety guard.

> **Status:** work in progress (core flow in place, more features planned).

---

## What it does

Ask a question like:

> "Which 5 customers placed the most orders last month?"

and the agent will:

1. Understand the question and build a curated prompt
2. Pull in the database context (schema, tables, columns)
3. Generate a PostgreSQL query
4. Run a safety check on the generated SQL
5. Execute the query (only if it is safe)
6. Summarize the result in plain language

If the safety check flags the query as unsafe, the agent **cancels** the request and tells you why instead of running it.

---

## Workflow

```
User question
     |
     v
Curate prompt  -->  Add DB context  -->  Generate SQL
                                              |
                                              v
                                       LLM safety check
                                        /           \
                                    safe             unsafe
                                      |                 |
                                      v                 v
                                 Execute SQL      Cancel + explain
                                      |
                                      v
                              Summarize results
                                      |
                                      v
                                   Answer
```

The flow is implemented as a graph in **LangGraph**, where each step is a node and the safety check decides which path is taken.

---

## Features

- Natural language to PostgreSQL query generation
- Schema-aware prompting so queries use real tables and columns
- LLM guard that reviews every query before it touches the database
- Graceful cancellation path for unsafe or unsupported requests
- Result summarization into a human-friendly answer

---

## Tech stack

| Area | Tools |
| --- | --- |
| Language | Python |
| Agent orchestration | LangGraph, LangChain |
| Database | PostgreSQL |
| LLM | [add your provider / model here] |

---

## Getting started

### Prerequisites

- Python 3.10+
- A running PostgreSQL database
- An API key for your LLM provider

### Installation

```bash
git clone https://github.com/rudra2609-06/ola_data_agent.git
cd ola_data_agent

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/your_db
LLM_API_KEY=your_api_key_here
```

> Adjust the variable names to match your code.

### Run

```bash
python main.py
```

> Replace `main.py` with your actual entry point.

---

## Example

```
Question : How many orders were placed per city?
SQL      : SELECT city, COUNT(*) FROM orders GROUP BY city;
Safety   : passed
Answer   : Mumbai had the most orders, followed by ...
```

```
Question : Delete all customers
Safety   : failed (destructive operation)
Answer   : Request cancelled. Only read-only analysis queries are allowed.
```

---

## Safety

- Every generated query goes through an LLM-based check before execution.
- Unsafe queries are never executed; the user gets a cancellation message instead.
- Recommended: connect with a **read-only** database user as an extra layer of protection.

---

## Roadmap

- [ ] Add automated tests for the SQL generation and guard nodes
- [ ] Support follow-up questions with conversation memory
- [ ] Add query retry on SQL errors
- [ ] Add a simple UI (Streamlit or FastAPI endpoint)

---

## Author

**Rudra Nimesh Thakkar**
BCA (Data Science) student, Manipal University Jaipur
GitHub: [rudra2609-06](https://github.com/rudra2609-06)
