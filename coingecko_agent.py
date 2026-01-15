import os
import json
import requests
import re
from dotenv import load_dotenv
from upsonic import Agent, Task

load_dotenv()
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
PUBLIC_BASE = "https://api.coingecko.com/api/v3"

class CoinGeckoAgent(Agent):
    def __init__(self):
        super().__init__(
            job_title="CoinGecko Crypto Agent",
            model="claude/claude-3-5-sonnet",
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

    def normalize_params(self, params: dict) -> dict:
        return {k: (str(v).lower() if isinstance(v, bool) else v) for k, v in params.items()}

    def extract_endpoint_and_params(self, user_text: str) -> dict | None:
        prompt = (
            "You are a tool that converts human requests into CoinGecko Pro API calls.  "
            "Given a user message, output ONE JSON object with two fields:\n"
            "  • path: the API path after /api/v3/, e.g. \"simple/price\"\n"
            "  • params: an object of the query parameters, e.g. {\"ids\":\"bitcoin\",\"vs_currencies\":\"usd\"}\n"
            "If the user is *not* asking for crypto data, reply with the single word `None`.\n\n"
            f"User message: \"{user_text}\""
        )
        resp = self.do(Task(prompt)).strip()
        if resp.lower() == "none":
            return None
        try:
            return json.loads(resp)
        except json.JSONDecodeError:
            return None

    def handle(self, user_text: str) -> str:
        text = user_text.strip()
        lower = text.lower()
        ep = self.extract_endpoint_and_params(lower)

        if not ep:
            return "⚠️ Couldn't understand your crypto request."

        path, params = ep["path"], self.normalize_params(ep.get("params", {}))

        # ── SPECIAL CASE: market_chart (1–7 days only) ────────────────────
        if path.endswith("/market_chart"):
            days_str = params.get("days", "")
            try:
                days = int(days_str)
            except Exception:
                days = None

            if days is None or days < 1 or days > 7:
                return f"⚠️ Historical charts are limited to 1–7 days. You asked for {days_str} days."

            coin = path.split("/")[1]
            try:
                resp = requests.get(
                    f"{PUBLIC_BASE}/coins/{coin}/market_chart",
                    params={"vs_currency": "usd", "days": days_str},
                    timeout=10
                )
                resp.raise_for_status()
                chart_data = resp.json()
            except Exception:
                return "⚠️ Sorry, couldn’t retrieve the market-chart data right now."

            prompt = (
                f"The user requested a {days}-day market chart of {coin.title()}.\n"
                f"JSON data:\n{json.dumps(chart_data, indent=2)}\n"
                "Summarize price, market-cap, and volume trends concisely."
            )
            return self.do(Task(prompt))

        # ── SPECIAL CASE: current market cap only ─────────────────────────
        if "market cap" in lower:
            m = re.search(r'(\d+)\s*days?', lower)
            if m and int(m.group(1)) > 1:
                return f"⚠️ I can only fetch the *current* market cap, not historical {m.group(1)}-day data."

            coin = params.get("ids") or (path.split("/")[1] if path.startswith("coins/") else None)
            if not coin:
                return "⚠️ Couldn't identify the coin for market cap."

            try:
                resp = requests.get(
                    f"{MCP_SERVER_URL}/simple/price",
                    params={
                        "ids": coin,
                        "vs_currencies": "usd",
                        "include_market_cap": "true"
                    },
                    timeout=10
                )
                resp.raise_for_status()
                data = resp.json().get(coin, {})
                cap = data.get("usd_market_cap")
                if cap:
                    return f"📊 The current market cap of {coin.title()} is ${cap:,.2f}."
                else:
                    return "⚠️ Couldn't retrieve the current market cap right now."
            except Exception:
                return "⚠️ Couldn't fetch the current market cap at the moment."

        # ── PREDEFINED ENDPOINT RESTRICTIONS ──────────────────────────────
        if path == "coins/list":
            return "⚠️ I can’t fetch the complete list of coins right now."

        if path.endswith("/market_chart/range"):
            try:
                span = (float(params.get("to", 0)) - float(params.get("from", 0))) / 86400
            except Exception:
                span = None
            if span is None or span > 7:
                return "⚠️ Historical chart ranges are limited to 7 days. Please adjust your range."

        if path.endswith("/ohlc"):
            allowed = {"1","7","14","30","90","180","365","max"}
            days = str(params.get("days","")).lower()
            if days not in allowed:
                return "⚠️ OHLC data only available for: 1, 7, 14, 30, 90, 180, 365 days or max."

        # ── FETCH FROM MCP PROXY ──────────────────────────────────────────
        full_url = f"{MCP_SERVER_URL}/{path}"
        try:
            resp = requests.get(full_url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return "⚠️ Couldn't retrieve that data right now or it's unavailable."

        # ── BUILD & SEND FINAL PROMPT TO CLAUDE ───────────────────────────
        prompt = (
            f"User requested: \"{text}\"\n\n"
            f"API JSON data ({path}):\n{json.dumps(data, indent=2)}\n"
            "Extract and respond only with specific values requested by the user, "
            "in friendly, concise language."
        )
        return self.do(Task(prompt))
