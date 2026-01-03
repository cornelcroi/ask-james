# ask-james

### Tired of copy/pasting between assistants just to get a second opinion?

`ask-james` ends that dance. It is an open-source Model Context Protocol (MCP) server that wraps your “ask another assistant what they think” habit into a single tool – `james.review`. James behaves like a trusted colleague who reviews designs or implementation plans, and because the server runs over stdio any MCP-compatible host (Claude desktop, Kiro, Cursor/Windsurf, custom orchestrators) can invoke him on demand.

Instead of bouncing between tabs, James gives you:

- one command (`ask-james`) to plug into any assistant
- a consistent persona that critiques, not rewrites
- flexible model backing via LiteLLM, so the review voice can be Claude today and GPT tomorrow

## Highlights

- **Single-focus tool** – `james.review` ingests a proposal plus contextual metadata and returns a JSON critique (summary, risks, questions to ask, positives, and next steps).
- **LLM-agnostic** – Uses [LiteLLM](https://github.com/BerriAI/litellm) so you can point James at any supported provider/model just by changing environment variables.
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

## Quick start (step-by-step)

1. **Install the package**

   ```bash
   pip install ask-james
   ```

2. **Add your API key + model to the MCP config**

   LiteLLM reads provider-specific environment variables (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Embed the correct pair for the provider you’re using directly in the MCP config. Example for OpenAI:

   ```json
   {
     "name": "Ask James",
     "command": "ask-james",
     "env": {
       "OPENAI_API_KEY": "sk-your-openai-key",
       "ASK_JAMES_MODEL": "gpt-5.2"
     }
   }
   ```

   Swap `OPENAI_API_KEY` for whichever variable LiteLLM expects (Anthropic, Google, Azure, Ollama, etc.).

3. **Register James with your MCP host**

   Drop the snippet above into the host’s MCP configuration file (`claude_desktop_config.json`, `mcp-tools.json`, etc.). Once saved, the host automatically launches James whenever you ask for a second opinion.

## Installation

```bash
pip install ask-james
```

Developers who want to edit locally can clone the repo and run `pip install -e .`, but PyPI is the recommended path for MCP hosts.

## Configuration

James relies on LiteLLM’s environment variables. Set your provider’s API key using the variable name LiteLLM expects (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) plus `ASK_JAMES_MODEL`. Optional knobs:

| Variable | Purpose |
| --- | --- |
| `ASK_JAMES_MODEL` | Default model alias/name for reviewer calls. Overrides `LITELLM_MODEL`. |
| `ASK_JAMES_MAX_TOKENS` | Hard cap on response size (defaults to `800`). |
| `ASK_JAMES_TEMPERATURE` | Floating point temperature override (defaults to `0.2`). |

Every request can also pass `model` or `temperature` inside the tool call to override the defaults. Full schema lives in `ask_james/server.py` if you need to inspect it.

## Running the server

Most MCP hosts expect a command that speaks stdio. Once installed you can point the host at:

```bash
ask-james
```

For local debugging you can also run `python -m ask_james` in a shell and pipe JSON-RPC payloads in/out (useful when testing with `socat` or custom clients).

## Using with LLM-based assistants

All hosts need the same three things:

1. `ask-james` installed on PATH (`pip install ask-james`).
2. An MCP config entry pointing to `ask-james`.
3. The LiteLLM credentials embedded in that config via an `env` block.

Use this template everywhere (swap the key name for your provider):

```json
{
  "name": "Ask James",
  "command": "ask-james",
  "env": {
    "OPENAI_API_KEY": "sk-your-openai-key",
    "ASK_JAMES_MODEL": "gpt-5.2"
  }
}
```

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "tools": [
    {
      "name": "Ask James",
      "command": "ask-james",
      "env": {
        "OPENAI_API_KEY": "sk-your-openai-key",
        "ASK_JAMES_MODEL": "gpt-5.2"
      }
    }
  ]
}
```

### Kiro (Settings → MCP Tools)

```json
{
  "id": "ask-james",
  "name": "Ask James",
  "command": "ask-james",
  "env": {
    "OPENAI_API_KEY": "sk-your-openai-key",
    "ASK_JAMES_MODEL": "gpt-5.2"
  }
}
```

### Cursor / Windsurf (`mcp-tools.json`)

```json
{
  "tools": [
    {
      "name": "Ask James",
      "command": "ask-james",
      "env": {
        "OPENAI_API_KEY": "sk-your-openai-key",
        "ASK_JAMES_MODEL": "gpt-5.2"
      }
    }
  ]
}
```

### Custom hosts / CLI orchestrators

Register the same structure in your MCP registry. Because the env block travels with the config, the host always launches James with the right key/model. Then call `james.review` with the JSON payload described below and parse the critique.

> **Security note:** These config files often live locally but still contain secrets. Store them in a secure location, avoid committing them to git, and rotate keys if the file is shared. Remember to replace `OPENAI_API_KEY` with the provider-specific variable LiteLLM expects if you’re not using OpenAI.

If your assistant does not expose a UI for MCP tools yet, you can still run James independently and send tool calls via the MCP JSON-RPC protocol (see `mcp` Python docs).

## Tool hints (how to talk to James)

James listens for whatever the primary assistant passes as the `proposal` and optional context. Here are a few prompts you can give your assistant (Claude, Kiro, Cursor, etc.) so it knows when to call `james.review`:

- *“Draft an MCP server plan, then ask James to critique it.”*
- *“Here’s an implementation plan—call James for a second opinion before finalizing.”*
- *“I’m about to send this customer response; ask James to flag any risks.”*
- *“Challenge this architecture with James and summarize what he worries about.”*

Typical output James sends back (summarized in plain language):

- **Summary** – Does the plan look solid overall? Should you proceed, tweak, or rethink?
- **Key concerns** – Explicit issues with severity, impact, and suggestions.
- **Questions** – Follow-ups James would ask the author.
- **Positive signals** – Parts that look good so you know what not to over-optimize.
- **Next steps & assumptions** – Actionable follow-ups and things to verify.

If you need to integrate James programmatically, the `james.review` tool accepts JSON fields like `proposal`, `context`, `review_focus`, `constraints`, `assumptions`, `risk_profile`, `max_questions`, `model`, and `temperature`; and it returns the structured fields shown above plus `model_used` and `raw_response`. Most hosts serialize these automatically, but the schema is available in `ask_james/server.py` if you need to inspect it directly.

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

Released under the MIT License. See `LICENSE` for details.
