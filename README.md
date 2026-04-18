# agent_upsonic

## Overview
This project serves as an intelligent orchestration layer integrating Model Context Protocol (MCP) servers with autonomous agents. By interacting through a Telegram bot, the system dynamically routes external Web3 API calls according to user prompts.

## Prerequisites
1. Create a Telegram bot (or use an existing one) and retrieve its token.
2. Obtain paid API keys for Glassnode and CoinGecko.

Create an `.env` file in the root directory and add the following variables:
```env
ANTHROPIC_API_KEY=
TELEGRAM_BOT_TOKEN=
GLASSNODE_API_KEY=
CG_API_KEY=
```

## Running the Project

**Note:** Run each of the following commands in a **separate terminal**.

**1. Start the MCP Servers:**
For CoinGecko:
```bash
uvicorn mcp_coingecko:app --port 8001
```

For Glassnode:
```bash
uvicorn mcp_glassnode:app --port 8002
```

**2. Run the Manager Agent:**
```bash
python manager_agent.py
```

Once all servers and the manager agent are running, you can begin interacting with your Telegram bot.
