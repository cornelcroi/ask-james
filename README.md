# ask-james

### Tired of copy/pasting between assistants just to get a second opinion?

`ask-james` ends that dance. It is an open-source Model Context Protocol (MCP) server that wraps your “ask another assistant what they think” habit into a single tool – `james.review`. James behaves like a trusted colleague who reviews designs or implementation plans, and because the server runs over stdio any MCP-compatible host (Claude desktop, Kiro, Cursor/Windsurf, custom orchestrators) can invoke him on demand.

Instead of bouncing between tabs, James gives you:

- one command (`ask-james`) to plug into any assistant
- a consistent persona that critiques, not rewrites
- flexible model backing via LiteLLM, so the review voice can be Claude today and GPT tomorrow

## Highlights

- **Single-focus tool** – `james.review` ingests a proposal plus contextual metadata and returns a JSON critique (summary, risks, questions to ask, positives, and next steps).
- **LLM-agnostic** – Uses [LiteLLM](https://github.com/BerriAI/litellm) so you can point James at any supported provider/model via environment config or a LiteLLM YAML file.
- **Named persona** – James never overwrites the primary assistant. He only critiques, surfaces assumptions, and suggests safer next steps.
- **Stdio transport** – Works out of the box with MCP clients such as the Claude desktop app or custom hosts.
- **Human-in-the-loop** – James never takes action; he just challenges the suggestion so you or the host assistant can choose the best final answer.

## Why this exists

Do you ever:

- ask your main assistant for a proposal,
- copy the whole thing into another assistant to get a “different take,” and
- paste the critique back into the first chat to reconcile it all manually?

That workflow is powerful but clunky. `ask-james` automates it without changing the way you think: you still own the conversation, you just say “ask James what he thinks,” and the second-opinion pass happens behind the scenes. James shows up with structured critique, assumptions to verify, and questions to ask—no tab juggling required.

**Best part:** it works in both directions. If you bounce between, say, Claude and Kiro, install `ask-james` in both. When you’re in Claude you can ask Kiro-for-James’s-take, and when you’re in Kiro you can pull Claude’s tone through the same tool. The review pattern stays consistent no matter which assistant you start with.

### When to use James

`ask-james` shines whenever you need to challenge an assistant’s suggestion before acting:

- **Implementation plans** – Your primary assistant proposes an architecture or refactor; James critiques it so you don’t blindly follow the first answer.
- **Product or policy decisions** – Use James to stress-test assumptions, hidden risks, or compliance angles before presenting a recommendation.
- **Support / operations workflows** – When an assistant suggests a customer-facing response, have James flag risky language or missing steps before sending it.
- **High-stakes automation** – Anytime acting on an LLM’s plan has real impact (deploys, refunds, irreversible operations), call James so the decision-maker (you or the host model) hears dissenting views.

James never takes the decision away: he is explicitly a reviewer. You (or the primary assistant) remain responsible for the final call, with James providing the structured critique that normally requires a second human.

## Quick start

1. **Install the server from PyPI**

   ```bash
   pip install ask-james
   ```

   (Developers can still clone the repo and run `pip install -e .` for local editing.)

2. **Configure LiteLLM (keys + model)**

   ```bash
   export OPENAI_API_KEY=sk-...
   export ASK_JAMES_MODEL=gpt-4o-mini   # or any LiteLLM alias
   ```

   > You can also supply a `litellm_config.yaml` if you prefer named routes.

3. **Run the server**

   ```bash
   ask-james   # or: python -m ask_james
   ```

4. **Tell your MCP host**

   Point the host’s configuration at the command above. Claude desktop, for example, expects an entry like:

   ```json
   {
     "name": "Ask James",
     "command": "ask-james"
   }
   ```

   Kiro, Cursor, and other MCP-aware assistants follow the same pattern: give the assistant a friendly name plus the `ask-james` command. Once added, “Ask James what he thinks” becomes an available tool call in the host UI.

## Installation

```bash
pip install -e .
```

(You can also package/publish it like any other Python project – it has a standard `pyproject.toml`.)

## Configuration

LiteLLM handles provider credentials. Point James at any model by either:

- Setting `ASK_JAMES_MODEL` (preferred) or `LITELLM_MODEL`, e.g. `export ASK_JAMES_MODEL=gpt-4o-mini`, **or**
- Providing a `litellm_config.yaml` with routing + keys and then referencing a model alias in `ASK_JAMES_MODEL`.

Optional environment variables:

| Variable | Purpose |
| --- | --- |
| `ASK_JAMES_MODEL` | Default model alias/name for reviewer calls. Overrides `LITELLM_MODEL`. |
| `ASK_JAMES_MAX_TOKENS` | Hard cap on response size (defaults to `800`). |
| `ASK_JAMES_TEMPERATURE` | Floating point temperature override (defaults to `0.2`). |

Every request can also pass a `model` field to override the default per tool call. See `ask_james/server.py` for additional knobs (max tokens, temperature, JSON schema).

### Example LiteLLM config

```yaml
model_list:
  - model_name: james-gpt4o
    litellm_params:
      model: gpt-4o-mini
      api_key: ${OPENAI_API_KEY}
  - model_name: james-claude
    litellm_params:
      model: anthropic/claude-3-5-sonnet
      api_key: ${ANTHROPIC_API_KEY}
```

Then point James at one of the aliases:

```bash
export ASK_JAMES_MODEL=james-gpt4o
```

Per-call overrides work the same way: pass `{"model": "james-claude"}` inside the tool arguments whenever you want a stricter reviewer.

## Running the server

Most MCP hosts expect a command that speaks stdio. Once installed you can point the host at:

```bash
ask-james
```

For local debugging you can also run `python -m ask_james` in a shell and pipe JSON-RPC payloads in/out (useful when testing with `socat` or custom clients).

## Using with LLM-based assistants

Any MCP-compatible assistant can treat James as a tool. Common examples:

- **Claude Desktop** – Preferences → Tools → “Add new tool”, then enter `ask-james`. Claude will surface James as an action (“Ask James what he thinks”) whenever the conversation calls for a second opinion.
- **Kiro / Cursor / Windsurf (VS Code)** – Add a new MCP tool in their settings or configuration JSON, pointing to the same command. Most IDE assistants let you toggle whether the tool is auto-invoked or only called when explicitly requested.
- **Custom orchestrators / CLI agents** – Register `ask-james` in your MCP tool registry and call `james.review` whenever the primary assistant wants a critique. Because the tool contract is pure JSON, you can feed/parse it programmatically.

If your assistant does not expose a UI for MCP tools yet, you can still run James independently and send tool calls via the MCP JSON-RPC protocol (see `mcp` Python docs for reference).

## Tool schema

`james.review` accepts the following JSON arguments:

```json
{
  "proposal": "string – required",
  "context": "string – optional",
  "review_focus": ["architecture", "operational risk"],
  "constraints": ["2-person team", "MVP timeline"],
  "assumptions": ["< 1k rps"],
  "risk_profile": "low | medium | high",
  "max_questions": 5,
  "model": "optional override",
  "temperature": 0.2
}
```

It always returns JSON shaped like:

```json
{
  "summary": "Overall judgment",
  "confidence": "low | medium | high",
  "key_concerns": [
    {
      "concern": "",
      "why_it_matters": "",
      "suggested_fix": "",
      "severity": "low | medium | high"
    }
  ],
  "questions": [""],
  "positive_signals": [""],
  "next_steps": [""],
  "assumptions_to_verify": [""],
  "raw_response": "original text in case parsing was lossy"
}
```

As long as James can produce JSON that matches this schema, any MCP client can interpret the critique programmatically.

### Sample request/response

```jsonc
// Tool call arguments sent by the host
{
  "proposal": "Implement MCP server with one review tool",
  "context": "Used by Claude desktop to double-check designs",
  "review_focus": ["simplicity", "safety"],
  "constraints": ["Must run over stdio"],
  "risk_profile": "medium"
}
```

Possible response from James:

```json
{
  "summary": "Clean single-tool design; make sure model config is explicit.",
  "confidence": "medium",
  "key_concerns": [
    {
      "concern": "No gating when to call James",
      "why_it_matters": "Hosts might overuse the tool",
      "suggested_fix": "Add policy to only call on implementation questions",
      "severity": "medium"
    }
  ],
  "positive_signals": ["Clear schema"],
  "questions": ["How do we choose models for different teams?"],
  "next_steps": ["Document trigger policy"],
  "assumptions_to_verify": ["Host handles arbitration"],
  "raw_response": "...",
  "model_used": "gpt-4o-mini"
}
```

## Recommendation / reasoning

- MCP stdio mode makes this trivial to embed into Claude, VS Code MCP hosts, or custom orchestrators without running a network service.
- LiteLLM keeps you model-neutral and instantly compatible with OpenAI, Anthropic, Google, Azure OpenAI, Ollama, etc. Changing James's voice is as simple as pointing at a different model alias.
- Keeping the tool count to one (`james.review`) matches the mental model: “ask James when you need a second opinion.” Future extensions (red-team mode, question-only mode) can live under the same namespace if needed.
- Persona-first design: James critiques, flags risks, and asks questions; the host model remains responsible for the final answer. This avoids “two agents arguing” and mirrors human peer review.

## Development

- Code lives under `ask_james/`. `server.py` houses the tool definition, prompt builder, and LiteLLM call.
- Install dev dependencies with `pip install -e .[dev]` (add your preferred extras, e.g., `ruff`, `pytest`).
- Run `python -m ask_james` for manual stdio testing.
- Tests are not bundled yet; contributions welcome!

## Contributing

Issues and pull requests are welcome. If you’re proposing substantial changes (new tools, new personas), please open an issue to discuss the use case so the “ask James” UX stays focused.

## License

Specify your preferred license (MIT/BSD/etc.) and drop it in `LICENSE`. Until then, treat the project as “all rights reserved.”
