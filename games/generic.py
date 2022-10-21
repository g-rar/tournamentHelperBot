from interactions import CommandContext, Option, OptionType
from models.registrationModels import RegistrationTemplate
from models.tournamentModels import Tournament

from utils import OptionTypes

from local.names import StringsNames

from contextExtentions.customContext import ServerContext, customContext
from controllers.tournamentController import tournamentController
from controllers.adminContoller import adminCommand

from bot import botGuilds, bot
from commands.tournamentCommands import tournamentBaseCommand

@tournamentBaseCommand.subcommand(
    name="add_generic",
    description="Run registration for any tournament, really.",
    options=[
        Option(  name="name", description="The tournament's name.",
                        type=OptionType.STRING, required=True),
        Option(  name="game", description="The game's name.",
                        type=OptionType.STRING, required=False),
    ])
@adminCommand
@customContext
async def addTournamentPlain(ctx:CommandContext, scx:ServerContext, name:str, game:str="🎮"):
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    if tournamentController.getTournamentFromName(ctx.guild_id, name):
        await scx.sendLocalized(StringsNames.TOURNAMENT_EXISTS_ALREADY, name=name)
        return
    # uncomment on completing template implementation
    # customTemplate = templatesController.getTemplate(ctx.guild_id, template) # returns [] if doesnt exist
    # customTemplate.participantFields += controller.PLAYER_FIELDS
    tournament = Tournament(
        name=name,
        hostServerId=int(ctx.guild_id),
        game= game if game else "any",
        registrationTemplate= RegistrationTemplate(name, int(ctx.guild_id))
    )
    if tournamentController.addTournament(tournament):
        await scx.sendLocalized(StringsNames.TOURNAMENT_ADDED, name=name, game=game)
    else:
        await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)
