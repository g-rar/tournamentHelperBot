from typing import List
from pymongo.database import Database
from pymongo.cursor import Cursor
import re
import asyncio
from discord_slash.context import ComponentContext, SlashContext
from discord_slash.utils import manage_components as mc

from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType
from discord.ext import commands
from bot import bot


async def setupButtonNavigation(ctx:SlashContext,paginationList:list,bot:commands.Bot):
    #Set up stuff
    current = 0
    prevButton = mc.create_button(
        label="Prev",
        custom_id="back",
        style=ButtonStyle.green
    )
    pageButton = mc.create_button(
        label = f"Page {int(paginationList.index(paginationList[current])) + 1}/{len(paginationList)}",
        custom_id = "cur",
        style = ButtonStyle.grey,
        disabled = True
    )
    nextButton = mc.create_button(
        label = "Next",
        custom_id = "front",
        style = ButtonStyle.green
    )
    actionRow = mc.create_actionrow( prevButton, pageButton, nextButton)

    #Sending first message
    mainMessage = await ctx.send(
        embed = paginationList[current],
        components = [actionRow]
    )
    #Infinite loop
    while True:
        #Try and except blocks to catch timeout and break
        try:
            btn_ctx: ComponentContext = await mc.wait_for_component(bot, components=actionRow, timeout=60)
            #Getting the right list index
            if btn_ctx.custom_id == "back":
                current -= 1
            elif btn_ctx.custom_id == "front":
                current += 1
            #If its out of index, go back to start / end
            if current == len(paginationList):
                current = 0
            elif current < 0:
                current = len(paginationList) - 1
            pageButton["label"] = f"Page {int(paginationList.index(paginationList[current])) + 1}/{len(paginationList)}"
            #Edit to new page + the center counter changes
            await btn_ctx.edit_origin(
                embed = paginationList[current],
                components = [ actionRow ]
            )
        except asyncio.TimeoutError:
            #Disable and get outta here
            prevButton['disabled'] = True
            nextButton['disabled'] = True
            await mainMessage.edit(components = [ actionRow ])
            break

def getQueryAsList(c:Cursor) -> list:
    ret = [val for val in c]
    return ret

def extractQuotedSubstrs(s) -> List[str]:
    patter = r'"([^"]*)"'

    matches = re.findall(patter, s)
    parts = re.split(patter, s)
    res = []

    for x in parts:
        if x in matches:
            res.append(x)
        else:
            res += x.split()

    return res


class OptionTypes:
    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    ANY = 9