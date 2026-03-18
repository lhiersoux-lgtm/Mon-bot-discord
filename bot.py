import discord
from discord.ext import commands
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client_ai = AsyncOpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

SYSTEM_PROMPT = """Tu es un assistant Discord sympa, décontracté et humain. Tu réponds naturellement, comme un ami. Tu es concis, friendly, tu peux faire des blagues. Tu parles français par défaut mais tu t'adaptes à la langue de l'utilisateur."""

conversation_history = {}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot connecté : {bot.user}")
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name="vos messages | !aide"))

async def get_ai_response(user_id, user_message, username):
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    conversation_history[user_id].append({"role": "user", "content": f"{username}: {user_message}"})
    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history[user_id]
    response = await client_ai.chat.completions.create(model="llama-3.1-8b-instant", messages=messages, max_tokens=500)
    reply = response.choices[0].message.content
    conversation_history[user_id].append({"role": "assistant", "content": reply})
    return reply

async def is_reply_to_bot(message):
    if message.reference is None:
        return False
    try:
        if message.reference.resolved is not None:
            return message.reference.resolved.author == bot.user
        ref = await message.channel.fetch_message(message.reference.message_id)
        return ref.author == bot.user
    except:
        return False

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return
    mentioned = bot.user in message.mentions
    replied = await is_reply_to_bot(message)
    if mentioned or replied:
        content = message.content
        for m in message.mentions:
            content = content.replace(f"<@{m.id}>", "").replace(f"<@!{m.id}>", "")
        content = content.strip() or "salut"
        async with message.channel.typing():
            try:
                reply = await get_ai_response(message.author.id, content, message.author.display_name)
                await message.reply(reply, mention_author=False)
            except Exception as e:
                print(f"Erreur: {e}")
                await message.reply("Désolé, petit souci. Réessaie !", mention_author=False)
        return
    await bot.process_commands(message)

@bot.command(name="reset")
async def reset(ctx):
    conversation_history.pop(ctx.author.id, None)
    await ctx.send(f"{ctx.author.mention} Conversation réinitialisée 👍")

@bot.command(name="aide")
async def aide(ctx):
    embed = discord.Embed(title="Comment me parler ?", color=discord.Color.blurple())
    embed.add_field(name="Me mentionner", value=f"{bot.user.mention} comment tu vas ?", inline=False)
    embed.add_field(name="Répondre à mes messages", value="Continue la conversation", inline=False)
    embed.add_field(name="!reset", value="Réinitialiser la conversation", inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

if __name__ == "__main__":
    bot.run(TOKEN, reconnect=True)
