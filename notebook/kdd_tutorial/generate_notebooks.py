"""Generate the AssetOpsBench KDD tutorial notebooks.

Run from anywhere with: uv run python notebook/kdd_tutorial/generate_notebooks.py
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


HERE = Path(__file__).resolve().parent


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": dedent(text).strip() + "\n"}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": dedent(text).strip() + "\n",
    }


def notebook(title: str, subtitle: str, cells: list[dict]) -> dict:
    intro = md(f"""
    # {title}

    {subtitle}

    **Tutorial contract:** run cells from top to bottom. Every external dependency is checked before use,
    outputs go under `artifacts/kdd_tutorial/`, and no credential value is printed.
    """)
    return {
        "cells": [intro, *cells],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


SETUP = code(r'''
from pathlib import Path
import json, os, sys

def find_repo(start=Path.cwd()):
    for candidate in [start, *start.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "src" / "servers").exists():
            return candidate
    raise RuntimeError("Open this notebook from inside the AssetOpsBench repository.")

REPO = find_repo()
ARTIFACTS = REPO / "artifacts" / "kdd_tutorial"
ARTIFACTS.mkdir(parents=True, exist_ok=True)
print("repo:", REPO)
print("python:", sys.version.split()[0])
''')

MCP_HELPER = code(r'''
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ENTRY_POINTS = {
    "iot": "iot-mcp-server", "utilities": "utilities-mcp-server",
    "fmsr": "fmsr-mcp-server", "wo": "wo-mcp-server",
    "tsfm": "tsfm-mcp-server", "vibration": "vibration-mcp-server",
}

async def mcp_session(server, operation, tool_name=None, arguments=None):
    params = StdioServerParameters(
        command="uv",
        args=["run", "--directory", str(REPO), ENTRY_POINTS[server]],
        cwd=str(REPO),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if operation == "list":
                return await session.list_tools()
            return await session.call_tool(tool_name, arguments or {})

def text_result(result):
    text = "\n".join(getattr(item, "text", str(item)) for item in result.content)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text

async def list_tools(server):
    response = await mcp_session(server, "list")
    return [{"name": t.name, "description": t.description, "schema": t.inputSchema} for t in response.tools]

async def call_tool(server, name, **arguments):
    return text_result(await mcp_session(server, "call", name, arguments))
''')

PREFLIGHT = code(r'''
import socket
from urllib.parse import urlparse

def tcp_reachable(url, timeout=1.0):
    parsed = urlparse(url)
    host, port = parsed.hostname or "localhost", parsed.port or 5984
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

COUCHDB_URL = os.getenv("COUCHDB_URL", "http://localhost:5984")
print("CouchDB reachable:", tcp_reachable(COUCHDB_URL), "at", COUCHDB_URL)
''')


def server_cells(server: str, overview: str, demo_cells: list[dict], requires: str) -> list[dict]:
    return [
        md(f"## Goal\n\n{overview}\n\n**Requires:** {requires}"),
        SETUP,
        MCP_HELPER,
        md("## 1. Discover the live MCP contract\n\nThis starts the real stdio server and asks it for its tool schemas."),
        code(f'tools = await list_tools("{server}")\n[(t["name"], list(t["schema"].get("properties", {{}}))) for t in tools]'),
        *demo_cells,
        md("## Takeaway\n\nYou exercised the server through MCP JSON-RPC over stdio—the same boundary the agents use."),
    ]


NOTEBOOKS = {
    "01_mcp_utilities.ipynb": notebook(
        "MCP server 1 — Utilities",
        "A fast, dependency-free first success that teaches the MCP request/response pattern.",
        server_cells("utilities", "Discover and call deterministic utility tools.", [
            md("## 2. Call two tools"),
            code('now = await call_tool("utilities", "current_date_time")\nenglish = await call_tool("utilities", "current_time_english")\nnow, english'),
            md("## 3. Read a JSON artifact through the server"),
            code('sample = ARTIFACTS / "utility_sample.json"\nsample.write_text(json.dumps({"tutorial": "KDD", "ready": True}), encoding="utf-8")\nawait call_tool("utilities", "json_reader", file_name=str(sample))'),
        ], "nothing beyond `uv sync`"),
    ),
    "02_mcp_iot.ipynb": notebook(
        "MCP server 2 — IoT and asset registry",
        "Compare installed sensors in the registry with measured sensors in telemetry.",
        server_cells("iot", "Walk from site → asset → installed/measured sensor inventory.", [
            md("## 2. CouchDB preflight"), PREFLIGHT,
            code('assert tcp_reachable(COUCHDB_URL), "Start CouchDB: docker compose -f src/couchdb/docker-compose.yaml up -d"'),
            md("## 3. Traverse the asset hierarchy"),
            code('sites = await call_tool("iot", "sites")\nsites'),
            code('assets = await call_tool("iot", "assets", site_name="MAIN")\nassets'),
            code('asset = "Chiller 6"\nmeasured = await call_tool("iot", "sensors", site_name="MAIN", asset_id=asset)\ninstalled = await call_tool("iot", "asset_sensors", site_name="MAIN", asset_id=asset)\ndetail = await call_tool("iot", "get_asset", site_name="MAIN", asset_id=asset)\n{"detail": detail, "measured": measured, "installed": installed}'),
        ], "seeded CouchDB (`docker compose -f src/couchdb/docker-compose.yaml up -d`)"),
    ),
    "03_mcp_fmsr.ipynb": notebook(
        "MCP server 3 — Failure modes and sensor relations",
        "Use curated failure-mode knowledge, then optionally map modes to sensors with an LLM.",
        server_cells("fmsr", "Retrieve curated chiller failure modes without model credentials.", [
            md("## 2. Curated, credential-free call"),
            code('failure_modes = await call_tool("fmsr", "get_failure_modes", asset_name="Chiller 6")\nfailure_modes'),
            md("## 3. Optional LLM-backed sensor mapping\n\nRun only when WatsonX credentials are configured."),
            code('required = ["WATSONX_APIKEY", "WATSONX_PROJECT_ID"]\nmissing = [name for name in required if not os.getenv(name)]\nprint("ready" if not missing else "skip mapping; missing: " + ", ".join(missing))'),
            code('if not missing:\n    mapping = await call_tool("fmsr", "get_failure_mode_sensor_mapping", asset_name="chiller", failure_modes=["Refrigerant leak", "Condenser fouling"], sensors=["temperature", "pressure", "flow"])\n    display(mapping)'),
        ], "none for curated Chiller/AHU modes; WatsonX credentials for unknown assets or mappings"),
    ),
    "04_mcp_workorders.ipynb": notebook(
        "MCP server 4 — Work orders",
        "Query operational work-order records safely in read-only mode.",
        server_cells("wo", "List, filter, and summarize work orders without mutating tutorial data.", [
            md("## 2. CouchDB preflight and read-only guard"), PREFLIGHT,
            code('assert tcp_reachable(COUCHDB_URL), "Start CouchDB before continuing"\nos.environ["AOB_READONLY"] = "1"\nprint("AOB_READONLY=1")'),
            md("## 3. Query the MAIN site"),
            code('orders = await call_tool("wo", "list_workorders", site_id="MAIN", page_size=5, page_num=1)\norders'),
            code('kpis = await call_tool("wo", "get_workorder_kpis", site_id="MAIN", period_months=12)\nkpis'),
            md("### Instructor note\n\nKeep writes out of the live tutorial. Demonstrate `generate_work_order` only in a disposable database."),
        ], "seeded CouchDB; this notebook forces `AOB_READONLY=1`"),
    ),
    "05_mcp_tsfm.ipynb": notebook(
        "MCP server 5 — Time-series foundation models",
        "Discover supported AI tasks and Granite TTM checkpoints before any expensive inference.",
        server_cells("tsfm", "Use lightweight catalog tools, then inspect the heavy tool contract.", [
            md("## 2. Static discovery calls (no Torch required)"),
            code('tasks = await call_tool("tsfm", "get_ai_tasks")\nmodels = await call_tool("tsfm", "get_tsfm_models")\n{"tasks": tasks, "models": models}'),
            md("## 3. Inspect forecasting inputs without running a model"),
            code('forecast = next(t for t in tools if t["name"] == "run_tsfm_forecasting")\nforecast["schema"]'),
            md("## 4. Optional inference\n\nFor a live run, install the TSFM extras/model assets and pass a real CSV path. Keep this cell disabled during the talk unless the checkpoint is already warm."),
            code('RUN_HEAVY_DEMO = False\nif RUN_HEAVY_DEMO:\n    result = await call_tool("tsfm", "run_tsfm_forecasting", dataset_path=str(REPO / "path/to/data.csv"), timestamp_column="timestamp", target_columns=["value"], forecast_horizon=24)\n    display(result)'),
        ], "nothing for discovery; Torch, Transformers, Granite TSFM, data, and checkpoints for inference"),
    ),
    "06_mcp_vibration.ipynb": notebook(
        "MCP server 6 — Vibration diagnostics",
        "Run useful DSP-domain calculations without a database, then show where telemetry joins the flow.",
        server_cells("vibration", "Calculate bearing frequencies and ISO severity through MCP.", [
            md("## 2. Credential-free bearing knowledge"),
            code('bearings = await call_tool("vibration", "list_known_bearings")\nbearings'),
            code('freqs = await call_tool("vibration", "calculate_bearing_frequencies", rpm=1800, n_balls=9, ball_diameter_mm=7.938, pitch_diameter_mm=38.5, contact_angle_deg=0, bearing_name="6205")\nfreqs'),
            code('severity = await call_tool("vibration", "assess_vibration_severity", rms_velocity_mm_s=4.5, machine_group="group2")\nseverity'),
            md("## 3. Optional data-backed path\n\nWith seeded CouchDB, call `get_vibration_data` first; use its returned `data_id` for FFT, envelope, and diagnosis."),
            PREFLIGHT,
        ], "NumPy/SciPy; CouchDB only for real vibration telemetry"),
    ),
}


NOTEBOOKS["07_end_to_end_stirrup.ipynb"] = notebook(
    "End to end — Stirrup agent execution",
    "Run one grounded multi-server scenario with the requested Stirrup agent and persist its trajectory.",
    [SETUP,
     md("## 1. Preflight\n\nStart with tools-only mode: it isolates MCP/model wiring from Docker code execution."),
     code('import shutil, subprocess\nassert shutil.which("uv"), "Install uv first"\nhelp_run = subprocess.run(["uv", "run", "--directory", str(REPO), "stirrup-agent", "--help"], text=True, capture_output=True)\nprint(help_run.stdout.splitlines()[0] if help_run.returncode == 0 else help_run.stderr)\nassert help_run.returncode == 0'),
     code('MODEL_ID = os.getenv("KDD_MODEL_ID", "watsonx/meta-llama/llama-4-maverick-17b-128e-instruct-fp8")\nrequired = ["WATSONX_APIKEY", "WATSONX_PROJECT_ID"] if MODEL_ID.startswith("watsonx/") else []\nmissing = [k for k in required if not os.getenv(k)]\nprint("model:", MODEL_ID)\nprint("credential preflight:", "ready" if not missing else "missing " + ", ".join(missing))'),
     md("## 2. Execute a multi-server scenario\n\nThe question requires IoT asset context, FMSR knowledge, and vibration reasoning. The trajectory is the input to evaluation."),
     code('TRACE_DIR = ARTIFACTS / "trajectories"\nTRACE_DIR.mkdir(exist_ok=True)\nQUESTION = "At site MAIN, inspect Chiller 6 sensors, list its failure modes, and explain which available vibration diagnostic would help investigate a bearing fault. Cite the tool evidence you used."\nRUN_ID, SCENARIO_ID = "kdd-stirrup-e2e", "kdd-e2e-001"'),
     code('if missing:\n    print("Skipped model call; configure credentials and rerun this cell.")\nelse:\n    env = os.environ.copy()\n    env["AGENT_TRAJECTORY_DIR"] = str(TRACE_DIR)\n    cmd = ["uv", "run", "--directory", str(REPO), "stirrup-agent", "--no-code", "--show-trajectory", "--model-id", MODEL_ID, "--run-id", RUN_ID, "--scenario-id", SCENARIO_ID, QUESTION]\n    completed = subprocess.run(cmd, env=env, text=True, capture_output=True)\n    print(completed.stdout)\n    if completed.returncode:\n        print(completed.stderr)\n    completed.check_returncode()'),
     md("## 3. Inspect the saved evidence"),
     code('trajectory_files = sorted(TRACE_DIR.glob("*.json"))\nprint([p.name for p in trajectory_files])\nif trajectory_files:\n    trajectory = json.loads(trajectory_files[-1].read_text())\n    display({k: trajectory.get(k) for k in ["run_id", "scenario_id", "runner", "model", "answer"]})'),
     md("## 4. Optional Stirrup code track\n\nUse a **separate leaderboard track**. For tutorial reliability, prefer Docker; use local only for trusted prompts that must read host files."),
     code('RUN_CODE_TRACK = False\nif RUN_CODE_TRACK and not missing:\n    cmd = ["uv", "run", "--directory", str(REPO), "stirrup-agent", "--code-enabled", "--code-backend", "docker", "--model-id", MODEL_ID, "--scenario-id", "kdd-code-001", "Use Python to compute the mean and population standard deviation of [2.1, 2.5, 3.0, 4.4]."]\n    subprocess.run(cmd, check=True, env=os.environ.copy())'),
    ],
)


NOTEBOOKS["08_evaluation.ipynb"] = notebook(
    "Evaluation — score saved Stirrup trajectories",
    "Join a scenario to the persisted trajectory, run the evaluator, and inspect both quality and operational metrics.",
    [SETUP,
     md("## 1. Materialize the scenario used by notebook 07"),
     code('SCENARIO_ID = "kdd-e2e-001"\nSCENARIO_FILE = ARTIFACTS / "kdd_e2e_scenario.json"\nscenario = [{"id": SCENARIO_ID, "text": "At site MAIN, inspect Chiller 6 sensors, list its failure modes, and explain which available vibration diagnostic would help investigate a bearing fault. Cite the tool evidence you used.", "type": "end_to_end", "characteristic_form": "The response must use grounded MCP evidence from IoT, failure-mode, and vibration capabilities; distinguish actual sensor inventory from available diagnostic methods; and avoid invented readings.", "scoring_method": "llm_judge"}]\nSCENARIO_FILE.write_text(json.dumps(scenario, indent=2), encoding="utf-8")\nSCENARIO_FILE'),
     md("## 2. Validate the join before spending a judge call"),
     code('TRACE_DIR = ARTIFACTS / "trajectories"\nfiles = sorted(TRACE_DIR.glob("*.json"))\nassert files, "Run notebook 07 first."\nrows = [json.loads(p.read_text()) for p in files]\n[(r.get("run_id"), r.get("scenario_id"), r.get("runner")) for r in rows]'),
     md("## 3. Run LLM-as-judge\n\nUse a judge model different from the execution model. The evaluator blocks self-judging."),
     code('import subprocess\nJUDGE_MODEL = os.getenv("KDD_JUDGE_MODEL", "litellm_proxy/azure/gpt-5.4")\nREPORTS = ARTIFACTS / "reports" / "stirrup_tools"\nREPORTS.mkdir(parents=True, exist_ok=True)\nprint("judge:", JUDGE_MODEL)'),
     code('RUN_JUDGE = False  # set True after configuring the judge provider\nif RUN_JUDGE:\n    cmd = ["uv", "run", "--directory", str(REPO), "evaluate", "--trajectories", str(TRACE_DIR), "--scenarios", str(SCENARIO_FILE), "--reports-dir", str(REPORTS), "--scorer-default", "llm_judge", "--judge-model", JUDGE_MODEL]\n    completed = subprocess.run(cmd, text=True, capture_output=True, env=os.environ.copy())\n    print(completed.stdout)\n    if completed.returncode:\n        print(completed.stderr)\n    completed.check_returncode()'),
     md("## 4. Inspect report artifacts"),
     code('aggregate_path = REPORTS / "_aggregate.json"\nif aggregate_path.exists():\n    aggregate = json.loads(aggregate_path.read_text())\n    display({"totals": aggregate.get("totals"), "by_scenario_type": aggregate.get("by_scenario_type"), "ops": aggregate.get("ops")})\nelse:\n    print("No report yet; set RUN_JUDGE=True after credentials are configured.")'),
     md("## Evaluation discipline\n\nPin scenario files, keep the judge distinct from the tested model, preserve trajectories for re-scoring, and report quality together with cost/latency/tool calls."),
    ],
)


NOTEBOOKS["09_leaderboard.ipynb"] = notebook(
    "Leaderboard — compare quality and operations",
    "Build a reproducible leaderboard from evaluator aggregates while keeping Stirrup tools-only and code tracks separate.",
    [SETUP,
     code('import pandas as pd\nREPORT_ROOT = ARTIFACTS / "reports"\naggregate_files = sorted(REPORT_ROOT.glob("**/_aggregate.json"))\nprint("aggregates:", len(aggregate_files))'),
     md("## 1. Load evaluator outputs\n\nFolder convention: name report folders like `stirrup_tools`, `stirrup_code`, `openai_tools`, etc."),
     code('rows = []\nfor path in aggregate_files:\n    report = json.loads(path.read_text())\n    folder = path.parent.name\n    inferred_track = "code" if "code" in folder.lower() else "tools-only"\n    totals, ops = report.get("totals", {}), report.get("ops", {})\n    for runner in report.get("runners", ["unknown"]):\n        for model in report.get("models", ["unknown"]):\n            rows.append({"track": inferred_track, "runner": runner, "model": model, "scenarios": totals.get("scenarios", 0), "pass_rate": totals.get("pass_rate", 0.0), "tool_calls": ops.get("tool_calls_total", 0), "tokens": ops.get("tokens_in_total", 0) + ops.get("tokens_out_total", 0), "latency_p50_ms": ops.get("duration_ms_p50"), "est_cost_usd": ops.get("est_cost_usd_total", 0.0), "source": str(path.relative_to(REPO))})\nboard = pd.DataFrame(rows)\nboard'),
     md("## 2. Rank within track\n\nPass rate is primary. Cost and median latency break ties; never rank code-enabled Stirrup against tools-only agents as if they had the same capabilities."),
     code('if not board.empty:\n    leaderboard = board.sort_values(["track", "pass_rate", "est_cost_usd", "latency_p50_ms"], ascending=[True, False, True, True], na_position="last").reset_index(drop=True)\n    leaderboard["rank_in_track"] = leaderboard.groupby("track").cumcount() + 1\n    leaderboard = leaderboard[["track", "rank_in_track", "runner", "model", "scenarios", "pass_rate", "est_cost_usd", "latency_p50_ms", "tool_calls", "tokens", "source"]]\n    display(leaderboard)\nelse:\n    leaderboard = board\n    print("No aggregates yet. Run notebook 08 for each runner/model configuration.")'),
     md("## 3. Export the auditable table"),
     code('LEADERBOARD_CSV = ARTIFACTS / "kdd_leaderboard.csv"\nleaderboard.to_csv(LEADERBOARD_CSV, index=False)\nLEADERBOARD_CSV'),
     md("## Reporting checklist\n\nPublish the scenario-set version, execution model, judge model, agent runner, track, sample count, pass rate, latency, tokens, estimated cost, and the aggregate file used for every row."),
    ],
)


for name, payload in NOTEBOOKS.items():
    (HERE / name).write_text(json.dumps(payload, indent=1), encoding="utf-8")

print(f"Wrote {len(NOTEBOOKS)} notebooks to {HERE}")
