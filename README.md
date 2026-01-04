# ask-james

**Get a second opinion from another LLM — without leaving your assistant.**

`ask-james` is an MCP server that lets any AI assistant (Claude, Kiro, Cursor, etc.) call out to a different LLM for a critical review. Say "ask James what he thinks" and get structured feedback on your plan before you commit.

## Example

Here's James in action during a Kiro CLI session:

```shell
> I need a list of POI in Paris using OpenStreetMap

Kiro: I'll create a Python script using the Overpass API...

    def get_paris_poi():
        query = """
        [out:json][timeout:25];
        (
          node["tourism"~"attraction|museum|monument|viewpoint"]["name"](area:3600071525);
          way["tourism"~"attraction|museum|monument|viewpoint"]["name"](area:3600071525);
        );
        out center meta;
        """
        # ... fetch and parse response

> Ask James for a second opinion

James:

  Your approach has solid foundations but several issues:

  Key concerns:
  - Filtering is too narrow — only tourism tags will miss landmarks
    tagged as historic, amenity, or leisure
  - Ways/relations don't have direct coordinates — you need out center;
  - "Top 50" is meaningless without defining how to rank POIs

  What looks solid:
  - Using Overpass API is the right approach
  - Querying nodes/ways/relations is correct

  Questions:
  - What exactly counts as a POI for your use case?
  - How should results be sorted — by name, importance, distance?
  - Paris city proper or greater metro area?
```

The assistant proposed code. James caught the gaps. Now you can decide with full context.

*Think about your last implementation — would a second opinion have saved you time?*

## Quick start

Add this to your MCP host config:

```json
{
  "command": "uvx",
  "args": ["ask-james"],
  "env": {
    "ASK_JAMES_API_KEY": "your-api-key",
    "ASK_JAMES_MODEL": "gpt-4o"
  }
}
```

That's it. `uvx` downloads and runs the package automatically.

## How it works

```
┌─────────────┐     "ask James"     ┌─────────────┐
│   Claude    │ ──────────────────► │  ask-james  │
│   / Kiro    │                     │ (MCP server)│
│   / Cursor  │ ◄────────────────── │             │
└─────────────┘    critique back    └──────┬──────┘
                                           │
                                           ▼
                                    ┌─────────────┐
                                    │  Any LLM    │
                                    │ (via LiteLLM)│
                                    └─────────────┘
```

- Your assistant sends the proposal to James via MCP
- James (powered by any LLM you choose) reviews it critically
- You get structured feedback: concerns, positives, questions, next steps
- James never rewrites — he only critiques

**Pro tip:** Use two different frontier models for best results. For example, Claude Opus 4.5 as your primary assistant with GPT-5.2 as James — or vice versa. Different models catch different blind spots.

## Configuration

| Variable | Description |
|----------|-------------|
| `ASK_JAMES_MODEL` | Model to use (e.g., `gpt-4o`, `claude-3-5-sonnet-20241022`) |
| `ASK_JAMES_API_KEY` | Your API key (works with any provider) |

Ask James supports **any model supported by [LiteLLM](https://docs.litellm.ai/docs/providers)** — OpenAI, Anthropic, Google, Azure, Ollama, and 100+ others.

Or omit `ASK_JAMES_API_KEY` and set the provider's native variable (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) — LiteLLM picks it up automatically.

## When to use James

- **Implementation plans** — Before blindly following an assistant's architecture
- **High-stakes changes** — Deploys, refunds, irreversible operations
- **Decisions under uncertainty** — When you want a dissenting view
- **Code review** — Quick sanity check on proposed changes

## Host configurations

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ask-james": {
      "command": "uvx",
      "args": ["ask-james"],
      "env": {
        "ASK_JAMES_API_KEY": "your-api-key",
        "ASK_JAMES_MODEL": "gpt-4o"
      }
    }
  }
}
```

### Kiro

Settings → MCP Tools:

```json
{
  "id": "ask-james",
  "name": "Ask James",
  "command": "uvx",
  "args": ["ask-james"],
  "env": {
    "ASK_JAMES_API_KEY": "your-api-key",
    "ASK_JAMES_MODEL": "gpt-4o"
  }
}
```

### Cursor / Windsurf

`mcp-tools.json`:

```json
{
  "tools": [
    {
      "name": "Ask James",
      "command": "uvx",
      "args": ["ask-james"],
      "env": {
        "ASK_JAMES_API_KEY": "your-api-key",
        "ASK_JAMES_MODEL": "gpt-4o"
      }
    }
  ]
}
```

## Prompting tips

Just tell your assistant to ask James:

- *"Ask James to critique this plan"*
- *"Get a second opinion from James before we proceed"*
- *"Have James review this code"*

## Development

```bash
pip install -e .
python -m ask_james  # manual stdio testing
```

## License

MIT
