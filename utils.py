from typing import List
from pymongo.database import Database
from pymongo.cursor import Cursor
import re
import asyncio
from discord_slash.context import SlashContext

from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType
from discord.ext import commands
from bot import bot


async def setupButtonNavigation(ctx:SlashContext,paginationList:list,bot:commands.Bot):
    #Sets a default embed
    current = 0
    #Sending first message
    #I used ctx.reply, you can use simply send as well
    mainMessage = await ctx.send(
        embed = paginationList[current],
        components = [ #Use any button style you wish to :)
            [
                Button(
                    label = "Prev",
                    id = "back",
                    style = ButtonStyle.green
                ),
                Button(
                    label = f"Page {int(paginationList.index(paginationList[current])) + 1}/{len(paginationList)}",
                    id = "cur",
                    style = ButtonStyle.grey,
                    disabled = True
                ),
                Button(
                    label = "Next",
                    id = "front",
                    style = ButtonStyle.green
                )
            ]
        ]
    )
    #Infinite loop
    while True:
        #Try and except blocks to catch timeout and break
        try:
            interaction = await bot.wait_for(
                "button_click",
                check = lambda i: i.component.id in ["back", "front"], #You can add more
                timeout = 60.0 #one minute of inactivity
            )
            #Getting the right list index
            if interaction.component.id == "back":
                current -= 1
            elif interaction.component.id == "front":
                current += 1
            #If its out of index, go back to start / end
            if current == len(paginationList):
                current = 0
            elif current < 0:
                current = len(paginationList) - 1

            #Edit to new page + the center counter changes
            await interaction.respond(
                type = InteractionType.UpdateMessage,
                embed = paginationList[current],
                components = [ #Use any button style you wish to :)
                    [
                        Button(
                            label = "Prev",
                            id = "back",
                            style = ButtonStyle.green
                        ),
                        Button(
                            label = f"Page {int(paginationList.index(paginationList[current])) + 1}/{len(paginationList)}",
                            id = "cur",
                            style = ButtonStyle.grey,
                            disabled = True
                        ),
                        Button(
                            label = "Next",
                            id = "front",
                            style = ButtonStyle.green
                        )
                    ]
                ]
            )
        except asyncio.TimeoutError:
            #Disable and get outta here
            await mainMessage.edit(
                components = [
                    [
                        Button(
                            label = "Prev",
                            id = "back",
                            style = ButtonStyle.green,
                            disabled = True
                        ),
                        Button(
                            label = f"Page {int(paginationList.index(paginationList[current])) + 1}/{len(paginationList)}",
                            id = "cur",
                            style = ButtonStyle.grey,
                            disabled = True
                        ),
                        Button(
                            label = "Next",
                            id = "front",
                            style = ButtonStyle.green,
                            disabled = True
                        )
                    ]
                ]
            )
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