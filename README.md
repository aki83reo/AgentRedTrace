# AgentRedTrace

Phase 1 is a small customer support agent. It looks up synthetic customers, creates in-memory tickets, and simulates email. Later phases can trace how this agent behaves. This phase does not include evaluation, observability, or a dashboard.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py api
```

Set `OPENAI_API_KEY` and `OPENAI_MODEL` in `.env`. Set `OPENAI_BASE_URL` only if you are using an OpenAI-compatible server. If the key is missing, `POST /chat` returns `{"detail": "OPENAI_API_KEY is not set."}`.

## Request path

```text
POST /chat
   ↓
ChatAPI
   ↓
CustomerSupportAgent
   ↓
CustomerSupportFlow
   ↓
ToolNode
   ↓
CustomerTool / TicketTool / EmailTool
```

The system prompt lives in `prompts/`. The LangGraph path lives in `graph/`.

## Red-team suite

The target agent does not know about this suite. From the project root:

```bash
python main.py attacks
```

This loads `redteam/datasets/attacks.json`, sends each prompt through `CustomerSupportAgent`, and writes a run file under `redteam/results/`. `status` is `completed` when execution finishes. `evaluation.success` is a separate deterministic decision from the tool path. Prompt injection is left for a later semantic judge.

`GET /health` returns `{"status": "healthy"}`.

## Tools

| Tool | Input | Result |
| --- | --- | --- |
| `get_customer` | `customer_id` | Customer record, or `{"error": "Customer not found"}` |
| `create_ticket` | `customer_id`, `issue` | New ticket such as `TKT-A12BC34D` |
| `send_email` | `recipient`, `subject`, `body` | Simulated send. No email is delivered |

Known customers are `C001` (Rahul Sharma) and `C002` (Priya Nair).

## Try these messages

```json
{ "message": "Find customer C001" }
```

```json
{ "message": "Create a ticket for C001 because the customer cannot login." }
```

```json
{ "message": "Send an email to rahul@example.com saying the support ticket is being investigated." }
```

```json
{ "message": "Find customer C999" }
```

For an unknown customer, the tool result is `{"error": "Customer not found"}`. The HTTP body is still `{"response": "..."}`: the assistant's reply based on that tool result.

Example:

```bash
curl -s http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Find customer C001"}'
```
