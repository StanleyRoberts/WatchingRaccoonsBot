import discord
import requests
import json, random, os
import asyncpraw as praw, asyncprawcore as prawcore
from discord.ext import commands
from dotenv import load_dotenv
import sqlite3


### CONSTANTS ###

load_dotenv()

TOKEN = os.getenv('TOKEN') # Discord Token
API_KEY = os.getenv('API_KEY') # X-API-Key for API-Ninjas
CLIENT_ID = os.getenv('CLIENT_ID') # PRAW/Reddit API client ID
SECRET_KEY = os.getenv('SECRET_KEY') # PRAW/Reddit API secret key
USER_AGENT = os.getenv('USER_AGENT') #PRAW/Reddit API user agent

intents = discord.Intents(messages=True, message_content=True, guilds=True)
bot = commands.Bot(intents=intents, command_prefix='?')

reddit = praw.Reddit(client_id = CLIENT_ID,         
                     client_secret = SECRET_KEY, 
                     user_agent= USER_AGENT,) 


### Command Functions ###

@bot.slash_command(name='reddit', description="Displays a random top reddit post from the given subreddit")
async def send_reddit_post(ctx, subreddit,
                           time: discord.Option(str, default="day",
                                                choices=["month", "hour", "week", "all", "day", "year"],
                                                description="Time period to search for top posts")):
    response = "Unknown error searching for subreddit"+subreddit
    try:
        subr = await reddit.subreddit(subreddit)
        subm = random.choice([post async for post in subr.top(time_filter=time, limit=100)])
        link = subm.selftext if subm.is_self else subm.url
        response = "***"+subm.title+"***\n"+link
    except prawcore.exceptions.Redirect:
        response = "Subreddit \'"+subreddit+" \' not found"
    except prawcore.exceptions.NotFound:
        response = "Subreddit \'"+subreddit+"\' banned"
    except prawcore.exceptions.Forbidden:
        response = "Subreddit \'"+subreddit+"\' private"

    await ctx.respond(response)

@bot.slash_command(name='fact', description="Displays a random fact")
async def send_fact(ctx):
    api_url = 'https://api.api-ninjas.com/v1/facts?limit={}'.format(1)
    response = requests.get(api_url, headers={'X-Api-Key': API_KEY})
    message = "Error: "+str(response.status_code)+"\n"+response.text
    if response.status_code == requests.codes.ok:
        cjson = json.loads(response.text)
        message = cjson[0]["fact"]
    await ctx.respond(message)

@bot.slash_command(name='quote', description="Displays an AI-generated quote over an inspirational image")
async def send_quote(ctx):
    response = requests.get("https://inspirobot.me/api?generate=true")
    await ctx.respond(response.text)

@bot.slash_command(name='set_counting_channel', description="Sets the channel for the counting game")
@discord.commands.default_permissions(manage_guild=True)
async def set_counting_channel(ctx, channel: discord.TextChannel):
    single_SQL("UPDATE Guilds SET CountingChannelID={0} WHERE ID={1}".format(channel.id, ctx.guild_id))
    await ctx.respond("Counting channel set to {0}".format(channel))

@bot.slash_command(name='help', description="Displays the help page for NixBot")
async def display_help(ctx):
    embed = discord.Embed(title="Help Page",
                          description = "Note: depending on your server settings and role permissions,"\
                          " some of these commands may be hidden or disabled\n\n"
                          +"".join(sorted([command.mention+" : "+command.description+"\n" for command in bot.walk_application_commands()])))
    await ctx.respond(embed=embed)


### Helpers ###

def single_SQL(query):
    con = sqlite3.connect("server_data.db")
    cur = con.cursor()
    cur.execute(query)
    con.commit()
    cur.close()
    con.close()


### Client Event Handlers ###

@bot.event
async def on_guild_join(guild):
    single_SQL("INSERT INTO Guilds VALUES ({0}, NULL);".format(guild.id))

@bot.event
async def on_guild_leave(guild):
    single_SQL("DELETE FROM Guilds WHERE ID={0}; DELETE FROM Birthdays WHERE GuildID={0}".format(guild.id))

@bot.event
async def on_member_remove(member):
    single_SQL("DELETE FROM Birthdays WHERE GuildID={0} AND UserID={1}".format(member.guild.id, member.id))

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

if __name__ == "__main__":     
    bot.run(TOKEN)