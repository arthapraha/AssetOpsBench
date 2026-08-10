# AssetOpsBench KDD tutorial — three-hour instructor path

The tutorial is a **hands-on** lab. The live path moves from a first
agent query, to the MCP tool calls behind it, and finally to scenario-based evaluation.

## Learning arc

1. **Use an agent:** ask an operational question and observe what happens.
2. **Open the black box:** inspect the MCP tools and grounded results used by the agent.
3. **Measure the agent:** connect a scenario to its trajectory and evaluation result.

## Hour 1 — Basic setup and agent hello world

### 0:00–0:30 — Repository warm-up

Open the [AssetOpsBench repository](https://github.com/IBM/AssetOpsBench) and follow the four
quick-start steps from `INSTRUCTIONS.md`, from the repository root:

```bash
# 1. Install the project environment
uv sync

# 2. Create the local configuration, then add credentials for one model provider
cp .env.public .env

# 3. Start CouchDB
docker compose -f src/couchdb/docker-compose.yaml up -d

# 4. Send one query to an agent (replace MODEL_ID with your configured model)
uv run stirrup-agent --no-code --model-id MODEL_ID "What sensors are on Chiller 6?"
```

The warm-up succeeds when the participant launches the command and can inspect either a result or
an actionable error. A perfect benchmark run is not required here.

Use these notebooks only when setup needs more guidance:

- `00_environment_setup.ipynb` — installation, Docker, credentials, kernel, and readiness checks.
- `00_mcp_agents_architecture.ipynb` — beginner concepts and AssetOpsBench architecture.

### 0:30–0:45 — What AssetOpsBench evaluates

Use the AssetOpsBench introduction and benchmark-pipeline sections of
`00_mcp_agents_architecture.ipynb`. Keep the detailed MCP explanation for Hour 2.

### 0:45–1:00 — Run two agentic questions

Use `01_agent_hello_world.ipynb`. Start with the two lightweight read-only questions:

```text
What sensors are on Chiller 6?
Is LSTM model supported in TSFM?
```

The work-order and multi-server examples in that notebook are optional extensions.

## Hour 2 — MCP tools and the AssetOpsBench ecosystem

### 1:00–1:15 — Look behind the answer

Return to the trajectory from the hello-world run. Distinguish the model's text from an actual MCP
tool call and its returned evidence. Then use the MCP architecture and tool-contract sections of
`00_mcp_agents_architecture.ipynb`.

### 1:15–1:35 — IoT MCP

Run the discovery and read-only examples in `02_mcp_iot.ipynb`. Focus on assets and installed or
measured sensors. This explains the tool path for “What sensors are on Chiller 6?”

### 1:35–2:00 — TSFM MCP

Use `05_mcp_tsfm_final.ipynb`. For the live session, run tool discovery, standardized tasks, series
profiling, and model search. The recipe-execution section is optional because it can take longer on
a new machine.

## Hour 3 — Scenario, trajectory, and evaluation

### 2:00–2:20 — One benchmark scenario

Use `07_end_to_end_stirrup_workorder_final.ipynb` as the main worked scenario. Explain the fixed
task, read-only safety constraint, run ID, scenario ID, and expected answer shape.

### 2:20–2:40 — Inspect the trajectory

In the same notebook, verify which tools executed, their arguments and outputs, and whether the
answer is grounded in those outputs. A plausible answer without an executed tool call is not a
successful tool-use trajectory.

### 2:40–3:00 — Evaluate

Run `08_evaluation_workorder_static_json.ipynb` to demonstrate pass rate and exact match from the
saved trajectory. `09_leaderboard.ipynb` is an optional closing view, not part of the core lab.

## Query menu

### Simple, single-server

```text
What sensors are on Chiller 6?
Is LSTM model supported in TSFM?
Get the work order of equipment CWC04013 for year 2017.
```

### Multi-step, multi-server

```text
What is the current date and time? Also list assets at site MAIN. Also get the sensor list and
failure-mode list for any chiller at site MAIN.
```

The multi-server query requires Utilities, IoT, and FMSR data/tools to be available. Treat it as a
demonstration after the two single-server questions, not as the first connectivity test.

## Optional reference notebooks

- `01_mcp_utilities.ipynb`
- `03_mcp_fmsr_fixed.ipynb`
- `04_mcp_workorders_final.ipynb`
- `06_mcp_vibration.ipynb`
- `07b_end_to_end_stirrup_workorder_advanced.ipynb`
- `09_leaderboard.ipynb`

Duplicate or older notebook variants are retained only for comparison. Use filenames ending in
`_final.ipynb` where available. Do not run `generate_notebooks.py` during the tutorial; it is a
maintenance generator and can overwrite hand-edited notebooks if it is out of date.

Generated tutorial outputs belong in `artifacts/kdd_tutorial/`. Keep tools-only and code-enabled
agent runs on separate leaderboard tracks.
