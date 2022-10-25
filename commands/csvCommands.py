from interactions import Channel, Choice, CommandContext, File, Message, Option, OptionType
from interactions.ext import files
import pandas as pd
import requests
from io import StringIO

from bot import bot, botGuilds
from local.lang.utils import utilStrs
from contextExtentions.customContext import ServerContext, customContext
from local.names import StringsNames

@bot.command(name="csv", scope=botGuilds)
async def csvBaseCommand(ctx:CommandContext): pass

@csvBaseCommand.subcommand(
    name="sort_by",
    description="Sort a csv file by the given column",
    options=[
        Option(
            name="column", description="The column to seed by.",
            type=OptionType.STRING, required=True
        ),
        Option(
            name="order", description="The order to aply",
            type=OptionType.STRING, required=True,
            choices=[
                Choice(name="ascending", value="a"),
                Choice(name="descending", value="")
            ]
        ),
        Option(
            name="message_id", description="Message in which the file is",
            type=OptionType.STRING, required=True
        ),
        Option(
            name="get_columns", description="If present, show only specified columns. Sepparate with commas.",
            type=OptionType.STRING, required=False
        )
    ]
)
@customContext
async def seedBy(ctx:CommandContext, scx:ServerContext, column:str, order:str, message_id:str, get_columns:str = None):
    order = bool(order)
    if not message_id.isdecimal():
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="message_id")
        return
    messageId = int(message_id)
    chn:Channel = ctx.channel
    try:
        msg:Message = await chn.get_message(message_id=messageId)
    except Exception as e:
        await scx.sendLocalized(StringsNames.MESSAGE_NOT_FOUND, data=type(e).__name__)
        return
    
    try:
        csvs:str = await getCsvTextFromMsg(msg)
        playersDF:pd.DataFrame = pd.read_csv(StringIO(csvs))

        await ctx.send(utilStrs.INFO.format("Seeding players..."))
        playersDF.sort_values(column, ascending=order, ignore_index=True, inplace=True)
        playersDF["Seed"] = playersDF.index + 1

        columnsList = None if not get_columns else get_columns.split(",")
        dfcsv = playersDF.to_csv(
            index=False,
            columns=columnsList,
            header= not columnsList or len(columnsList)!=1
        )
        await files.command_send(ctx, content= utilStrs.INFO.format("File generated"), files=[File(fp=StringIO(dfcsv), filename="Seeding.csv")])
        
    except Exception as e:
        await ctx.send(utilStrs.ERROR.format(e))
        raise e

@csvBaseCommand.subcommand(
    name="get_columns",
    description="Given a csv file in this text channel, get the columns as a sepparate file",
    options=[
        Option(
            name="columns", description="The columns to get. Sepparate using commas.",
            type=OptionType.STRING, required=True
        ),
        Option(
            name="message_id", description="Message in which the file is",
            type=OptionType.STRING, required=True
        ),
    ]
)
@customContext
async def getColumn(ctx:CommandContext, scx:ServerContext, columns:str, message_id:str):
    if not message_id.isdecimal():
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="message_id")
        return
    messageId = int(message_id)
    chn:Channel = ctx.channel
    try:
        msg:Message = await chn.get_message(messageId)
    except Exception as e:
        await scx.sendLocalized(StringsNames.MESSAGE_NOT_FOUND, data=type(e).__name__)
        return
    try:
        csvs:str = await getCsvTextFromMsg(msg)
        playersDF:pd.DataFrame = pd.read_csv(StringIO(csvs))
        columnList = columns.split(",")
        dfcsv = playersDF.to_csv(index=False, columns=columnList, header=(len(columnList)!=1))
        await files.command_send(ctx,
            content=utilStrs.INFO.format("File generated"),
            files=[File(fp=StringIO(dfcsv), filename="Seeding.csv")]
        )
    except Exception as e:
        await ctx.send(utilStrs.ERROR.format(e))



async def getCsvTextFromMsg(msg:Message):
    if not msg.attachments:
        raise Exception("Did not find any CSV file")
    file_url = msg.attachments[0].url
    req = requests.get(file_url)
    if req.status_code == 200:
        return req.content.decode('utf-8')
    else:
        raise Exception("Could not read CSV file")