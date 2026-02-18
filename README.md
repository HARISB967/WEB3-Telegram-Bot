# crypto_agent_upsonic


create a telegram bot or use an old bot , retrieve its token.
for glassnode and coingecko use its paid api keys.

in env file , add these variables:
ANTHROPIC_API_KEY = 
TELEGRAM_BOT_TOKEN = 
GLASSNODE_API_KEY = 
CG_API_KEY=  

terminal commands given in ""
##every command in seperate terminals##

to start mcp servers: 

coingecko: " uvicorn mcp_coingecko:app --port 8001  "


glassnode: " uvicorn mcp_glassnode:app --port 8002  "

to run manager agent:   " python manager_agent.py "

now interact with the given telegram bot of yours
