# glassnode_agent.py
import os
import time
import json
import requests
from dotenv import load_dotenv
from upsonic import Agent, Task

load_dotenv()
GLASSNODE_MCP_URL = os.getenv("GLASSNODE_MCP_URL", "http://localhost:8002")

# Valid metrics known to be supported by Glassnode
VALID_METRIC_PATHS = {
    "supply/current",
    "addresses/active_count",
    "addresses/count",
    "transactions/transfers_volume_exchanges_net",
    "derivatives/futures_open_interest_sum",
    "distribution/balance_exchanges_relative",
    "lightning/network_capacity_sum",
    "defi/total_value_locked"
}

# Snapshot metrics that do NOT require s/u timestamps
SNAPSHOT_PATHS = {
    "supply/current",
    "addresses/active_count",
    "addresses/count",
    "derivatives/futures_open_interest_sum",
    "lightning/network_capacity_sum",
    "defi/total_value_locked"
}

"""
class GlassnodeAgent(Agent):
    def __init__(self):
        super().__init__(
            job_title="Glassnode On-Chain Agent",
            model="claude/claude-3-5-sonnet",
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
"""
class GlassnodeAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Glassnode On-Chain Agent",      
            model="anthropic/claude-3-5-sonnet"   
            
        )


    def parse_request(self, user_text: str) -> dict | None:
        prompt = (
            "You are a tool that converts user questions into Glassnode API calls.\n"
            "Return a JSON object with:\n"
            "• path: one of the following metric paths:\n"
            f"{', '.join(VALID_METRIC_PATHS)}\n"
            "• asset: e.g. BTC, ETH\n"
            "• params: optional dictionary like {\"interval\": \"24h\"}\n\n"
            "Respond only with the JSON. If invalid, reply: None.\n\n"
            f"User: \"{user_text}\""
        )
        raw = self.do(Task(prompt)).strip()
        if raw.lower() == "none":
            return None
        if raw.startswith("```"):
            raw = raw.strip("```").strip()
        try:
            return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except json.JSONDecodeError:
            return None

    def handle(self, user_text: str) -> str:
        parsed = self.parse_request(user_text)
        if not parsed or "path" not in parsed or "asset" not in parsed:
            return "⚠️ Failed to understand your Glassnode request."

        path = parsed["path"]
        asset = parsed["asset"]
        params = parsed.get("params", {})
        params["a"] = asset

        # Validate path early to prevent 404
        if path not in VALID_METRIC_PATHS:
            return f"⚠️ Sorry, the metric '{path}' is not supported right now."

        # Only add time-range for time-series metrics
        if path not in SNAPSHOT_PATHS:
            now = int(time.time())
            interval = params.get("interval", "24h")
            try:
                num = int(''.join(filter(str.isdigit, interval)))
                unit = ''.join(filter(str.isalpha, interval)).lower()
                delta = num * 86400 if unit == "d" else num * 3600
            except:
                delta = 86400
            params.setdefault("s", now - delta)
            params.setdefault("u", now)

        # Build request URL
        url = f"{GLASSNODE_MCP_URL}/glassnode/{path}"
        print(f"[GlassnodeAgent] GET {url} params={params}")

        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception:
            return "⚠️ Sorry, I couldn’t retrieve that Glassnode data right now."

        if isinstance(data, list) and len(data) > 30:
            data = data[-30:]

        summary_prompt = (
            "You are a blockchain analyst summarizing real on-chain metrics.\n"
            "• Never refer to yourself or mention Glassnode or any tools.\n"
            "• Use phrasing like 'The data shows...', 'We observe...', etc.\n\n"
            f"Metric: {path}\n"
            f"Recent Data:\n{json.dumps(data[-3:], indent=2)}\n\n"
            "Provide a professional and concise trend summary."
        )
        return self.do(Task(summary_prompt))
