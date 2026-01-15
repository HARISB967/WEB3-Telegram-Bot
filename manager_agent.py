import os
import telebot
from dotenv import load_dotenv
from upsonic import Agent, Task
from coingecko_agent import CoinGeckoAgent
from glassnode_agent import GlassnodeAgent

# ── Load environment variables ───────────────────────────────
load_dotenv()
bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

# ── Initialize Main Router Agent ──────────────────────────────
manager_agent = Agent(
    job_title="",
    model="claude/claude-3-5-sonnet",
    api_key=anthropic_api_key,
    system_message=(
        "You are an internal router for a chatbot system. "
        "Your job is to silently decide which specialized assistant agent should handle the user message. "
        "Respond with exactly one agent name (like Crypto), or reply: General.\n"
        "Never introduce yourself or explain your role. "
        "Just do the routing cleanly without exposing any internal logic."
    )
)

# ── Initialize Specialized Agents ─────────────────────────────
AGENTS = {
    "Crypto": CoinGeckoAgent(),
    "Onchain": GlassnodeAgent()
   
}

# ── Routing Logic ─────────────────────────────────────────────
def route_message(text: str) -> str:
    agent_list = ', '.join(AGENTS.keys())
    routing_prompt = (
    "Decide which assistant should handle this message.\n"
    f"Available options: {agent_list}, General.\n\n"
    "• Crypto → if the request involves CoinGecko data like price, market cap, volume, charts.\n"
    "• Onchain → if the user asks for Glassnode metrics like supply, addresses, fees, NUPL, MVRV, etc.\n"
    "• General → for greetings or unrelated questions.\n\n"
    f"Message: \"{text}\"\n\n"
    "Reply with exactly one agent name."
)


    selected = manager_agent.do(Task(routing_prompt)).strip()
    agent = AGENTS.get(selected)

    if agent:
        return agent.handle(text)

    # Fallback: general small talk or unknown topic
    general_prompt = f"The user says: \"{text}\". Respond in a helpful and conversational way."
    return manager_agent.do(Task(general_prompt))

# ── Telegram Handlers ─────────────────────────────────────────
@bot.message_handler(commands=['start', 'help'])
def welcome(msg):
    bot.reply_to(msg, "👋 Hi! You can ask crypto questions like price, market cap or just chat.")

@bot.message_handler(func=lambda _: True)
def handle_all(msg):
    reply = route_message(msg.text)
    bot.reply_to(msg, reply)

# ── Run Polling ───────────────────────────────────────────────
if __name__ == "__main__":
    bot.infinity_polling(timeout=60, long_polling_timeout=20)
