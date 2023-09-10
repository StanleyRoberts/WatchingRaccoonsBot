from discord.ext import commands
import discord
import requests
import typing
import json
import re
from characterai import PyAsyncCAI as PyCAI

from helpers.style import Colours
from helpers.env import HF_API, CAI_CHAR_TOKEN as TOKEN, CAI_NIX_ID
from helpers.logger import Logger
from helpers.style import Emotes

logger = Logger()

USER_QS = ["Who are you?", "Is Stan cool?", "What is your favourite server?", "Where do you live?"]
NIX_AS = ["I am Nix, a phoenix made of flames", "Yes, I think Stan is the best!",
          "I love the Watching Racoons server the most!",
          "I live in a volcano with my friends: DJ the Dragon and Sammy the Firebird."]


class Misc(commands.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    @commands.slash_command(name='quote', description="Displays an AI-generated quote over an inspirational image")
    async def send_quote(self, ctx: discord.ApplicationContext) -> None:
        await ctx.respond(requests.get("https://inspirobot.me/api?generate=true").text)
        logger.info("Generating quote", member_id=ctx.author.id, channel_id=ctx.channel_id)

    @commands.slash_command(name='all_commands', description="Displays all of Nix's commands")
    async def display_help(self, ctx: discord.ApplicationContext) -> None:
        desc = ("Note: depending on your server settings and role permissions," +
                " some of these commands may be hidden or disabled\n\n" +
                "".join(["\n***" + cog + "***\n" + "".join(sorted([command.mention + " : " + command.description + "\n"
                                                                   for command in self.bot.cogs[cog].walk_commands()]))
                        for cog in self.bot.cogs]))  # Holy hell
        embed = discord.Embed(title="Help Page", description=desc,
                              colour=Colours.PRIMARY)
        await ctx.respond(embed=embed)
        logger.info("Displaying long help", member_id=ctx.author.id, channel_id=ctx.channel_id)

    @commands.slash_command(name='help', description="Display the help page for Nix")
    async def helper_embed(self, ctx: discord.ApplicationContext) -> None:
        view = Help_Nav(self.bot.cogs)
        await ctx.interaction.response.send_message(embed=view.build_embed(),
                                                    view=view)
        logger.info("Displaying short help", member_id=ctx.author.id, channel_id=ctx.channel_id)

    @commands.Cog.listener("on_message")
    async def NLP(self, msg: discord.Message) -> None:
        """
        Prints out an AI generated response to the message if it mentions Nix

        Args:
            msg (discord.Message): Message that triggered event
        """
        if (self.bot.user.mentioned_in(msg) and msg.reference is None):
            logger.info("Generating AI response", member_id=msg.author.id, channel_id=msg.channel.id)
            clean_prompt = re.sub(" @", " ",
                                  re.sub("@" + self.bot.user.name, "", msg.clean_content))
            client = PyCAI(TOKEN)
            await client.start()
            chat = await client.chat.new_chat(CAI_NIX_ID)
            if not chat:
                return
            participants = chat['participants']
            if not participants[0]['is_human']:
                nix_username = participants[0]['user']['username']
            else:
                nix_username = participants[1]['user']['username']
            data = await client.chat.send_message(chat['external_id'], nix_username, clean_prompt, wait=True)
            text = data['replies'][0]['text']
            await msg.reply(text)


class Help_Nav(discord.ui.View):
    def __init__(self, cogs: typing.Mapping[str, discord.Cog]) -> None:
        super().__init__()
        self.index = 0
        self.pages = ["Front"] + [cogs[cog] for cog in cogs]

    def build_embed(self):
        self.index = self.index % len(self.pages)
        page = self.pages[self.index]

        compass = "|".join([f" {page.qualified_name} " if page != self.pages[self.index]
                            else f"** {page.qualified_name} **" for page in self.pages[1:]]) + "\n"
        if page == "Front":
            desc = compass + ("\nNote: depending on your server settings and role permissions, " +
                              "some of these commands may be hidden or disabled")
        else:
            desc = compass + ("\n***" + page.qualified_name + "***:\n" + ""
                              .join(sorted([command.mention + " : " + command.description + "\n"
                                            for command in page.walk_commands()])))

        return discord.Embed(title="Help Page", description=desc,
                             colour=Colours.PRIMARY)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji='⬅️')
    async def backward_callback(self, _, interaction: discord.Interaction) -> None:
        self.index -= 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        logger.debug("Back button pressed", member_id=interaction.user.id)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, emoji='➡️')
    async def forward_callback(self, _, interaction: discord.Interaction) -> None:
        self.index += 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        logger.debug("Next button pressed", member_id=interaction.user.id)


def setup(bot: discord.Bot) -> None:
    bot.add_cog(Misc(bot))
