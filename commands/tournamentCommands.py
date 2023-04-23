import asyncio
from interactions import Channel, ChannelType, CommandContext, Embed, File, Guild, Message, MessageReaction, Option, OptionType
from interactions.ext.paginator import Page, Paginator
from interactions.ext import files, wait_for
import pandas as pd
from dataclasses import asdict
from datetime import datetime
from io import StringIO
from pprint import pformat

from bot import bot, botGuilds
from httpClient import getAllUsersFromReaction
from local.lang.utils import utilStrs
from contextExtentions.customContext import ServerContext, customContext
from local.names import StringsNames

from models.tournamentModels import Tournament, TournamentStatus

from controllers.adminContoller import adminCommand
from controllers.playerController import participantController
from controllers.tournamentController import tournamentController
from games import factories

from commands.registrationCommands import registrationBase

from utils.utils import paginatorButtons, spaceStrings


@bot.command(name="tournaments", scope=botGuilds)
async def tournamentBaseCommand(ctx:CommandContext): pass

@tournamentBaseCommand.subcommand(
    name="delete",
    options=[
        Option(name="tournament",description="Tournament to delete",
                type=OptionType.STRING, required=True)
    ],
    description="Deletes a tournament from existence"
)
@adminCommand
@customContext
async def deleteTournament(ctx:CommandContext, scx:ServerContext, tournament:str):
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    guild:Guild = ctx.guild # this could be None
    tournamentData = tournamentController.getTournamentFromName(guild.id, tournament)
    if not tournamentData:
        await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    if tournamentData.registration.status != TournamentStatus.REGISTRATION_CLOSED:
        await registrationBase.coroutines['close'](ctx, scx=scx, tournament = tournament)
    if tournamentController.deleteTournament(tournamentData):
        await scx.sendLocalized(StringsNames.TOURNAMENT_DELETED, name=tournament)
    else:
        await scx.sendLocalized(StringsNames.DB_DROP_ERROR)

@tournamentBaseCommand.subcommand(
    name="view",
    options=[
        Option(name="tournament", description="Get the details for one tournament",
               type=OptionType.STRING, required=False),
        Option(name="show_games", description="Show the games for each tournament",
                type=OptionType.BOOLEAN, required=False)
    ],
    description="Shows a list of the tournaments made by this server"
)
@customContext
async def getTournaments(ctx: CommandContext, scx: ServerContext, tournament:str = None, show_games:bool = False):
    guild:Guild = ctx.guild
    if tournament:
        tournamentData = tournamentController.getTournamentFromName(int(guild.id), tournament)
        if tournamentData:
            #TODO this can be further prettyfied
            e = tournamentController.getTournamentEmbed(tournamentData, scx.server.language)
            e.set_thumbnail(ctx.guild.icon_url)
            await ctx.send(embeds=e)
        else:
            await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    tournaments:list[Tournament] = tournamentController.getTournamentsForServer(ctx.guild_id)
    if len(tournaments) > 20:
        pageList = []
        embedTournaments = []
        page = 1
        for i in range(len(tournaments)):
            tournament:Tournament = tournaments[i]
            game = f"({tournament.game})"
            tournamentStr = f'- `{spaceStrings(tournament.name, tournament.game, 40) if show_games else tournament.name}`'
            if tournament.registration.status != TournamentStatus.CHECK_IN_CLOSED:
                tournamentStr = f" {tournamentStr} [ 📝 ]"
            embedTournaments.append(tournamentStr)
            # every 20 tournaments or when the last tournament is reached
            if (i+1) % 20 == 0 or i == len(tournaments)-1:
                tournamentStr = "\n".join(embedTournaments)
                embed = Embed(
                    title=f"Showing tournaments from { tournaments[i-19].name } to { tournaments[i].name }", 
                    color=0xFFBA00, 
                    description="\n"+tournamentStr, 
                    timestamp=datetime.utcnow())
                embed.set_thumbnail(url=guild.icon_url)
                embed.set_footer(text="TournamentHelper Bot")
                pageList.append(Page(f"{guild.name} (P. #{page})", embed))
                embedTournaments = []
                page += 1
        await Paginator(bot, ctx, pageList, use_index=True, buttons=paginatorButtons).run()
    else:
        tournamentStr = ""
        for t in tournaments:
            game = f"({t.game})"
            tournamentStr += f'- `{spaceStrings(t.name, game, 40) if show_games else t.name}`'
            if t.registration.status != TournamentStatus.CHECK_IN_CLOSED:
                tournamentStr = f" {tournamentStr} [ 📝 ]"
            tournamentStr += "\n"
        embed = Embed(
            title=guild.name, 
            color=0xFFBA00, 
            description="The tournaments in this server are:\n"+tournamentStr, 
            timestamp=datetime.utcnow())
        embed.set_thumbnail(url=guild.icon_url)
        embed.set_footer(text="TournamentHelper Bot")
        await ctx.send(embeds=[embed])

@tournamentBaseCommand.subcommand(
    name="edit_name",
    options=[
        Option(name="old_name", description="Tournament to edit",
               type=OptionType.STRING, required=True),
        Option(name="new_name", description="New name for the tournament",
               type=OptionType.STRING, required=True),
    ]
)
@adminCommand
@customContext
async def editTournament(
        ctx: CommandContext,
        scx: ServerContext,
        old_name: str,
        new_name: str
    ):
    tournamentObj = tournamentController.getTournamentFromName(ctx.guild_id,old_name)
    tournamentCtrl = factories.getControllerFor(tournamentObj)
    if tournamentObj is None:
        await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=old_name)
        return
    newTor = tournamentController.getTournamentFromName(ctx.guild_id, new_name)
    if newTor is not None:
        await scx.sendLocalized(StringsNames.TOURNAMENT_EXISTS_ALREADY, name=new_name)
        return
    tournamentObj.name = new_name
    if tournamentController.updateTournament(tournamentObj):
        await scx.sendLocalized(StringsNames.TOURNAMENT_UPDATED, name=new_name)
    else:
        await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)



@bot.command(name="check-in", scope=botGuilds)
async def checkInBaseCommand(ctx:CommandContext): pass

@checkInBaseCommand.subcommand(
    name="read_from_reaction",
    description="Register people who reacted to a certain message as checked in",
    options= [
        Option(name="tournament", description="The tournament for which this check in counts for.",
               type=OptionType.STRING, required=True),
        Option(name="message_id", description="Message id at which users reacted for check-in, (you can get this by right clicking the message)",
               type=OptionType.STRING, required=True),
        Option(name="channel", description="The channel in which the specified message is",
               type=OptionType.CHANNEL, required=True)
    ]
)
@adminCommand
@customContext
async def readCheckIns(ctx:CommandContext,
        tournament:str, 
        scx:ServerContext,
        message_id:str,
        channel:Channel):
    tournamentObj = tournamentController.getTournamentFromName(ctx.guild_id,tournament)
    tournamentCtrl = factories.getControllerFor(tournamentObj)
    if tournamentObj is None:
        await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    if not message_id.isdecimal():
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="message_id")
        return
    messageId = int(message_id)
    if channel.type != ChannelType.GUILD_TEXT:
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_TEXT_CHANNEL, option="channel")
        return
    try:
        msg:Message = await channel.get_message(messageId)
    except Exception as e:
        await scx.sendLocalized(StringsNames.MESSAGE_NOT_FOUND, data=type(e).__name__)
        return
    
    def check(reaction:MessageReaction):
        return int(reaction.user_id) == int(ctx.author.id)
    try:
        res1 = await scx.sendLocalized(StringsNames.INPUT_CHECK_IN_REACTION)
        inputReaction:MessageReaction= await wait_for.wait_for(bot, 'on_message_reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await scx.sendLocalized(StringsNames.REACTION_TIMEOUT, time="60")
        return
    reaction = await getAllUsersFromReaction(
        int(channel.id), int(msg.id) , inputReaction.emoji.name
    )
    if reaction == []:
        await scx.sendLocalized(StringsNames.NO_REACTION_IN_MSG, reaction=str(inputReaction.emoji))
        return
    participants = []
    for user in reaction:
        p = participantController.getParticipantFromDiscordId(int(user.get('id')), tournamentObj._id)
        if p is None: continue
        pData = tournamentCtrl.getParticipantView(p)
        participants.append(pData)

    df = pd.DataFrame(participants)
    await files.command_send(ctx, files=[File(fp=StringIO(df.to_csv()), filename= f"Participants_{datetime.utcnow()}.csv")])
