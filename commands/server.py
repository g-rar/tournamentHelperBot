from controllers.admin import adminCommand
from controllers.server import Server, serverController

import strings as strs

from discord_slash.context import SlashContext

from bot import botGuilds, slash
from devCommands.devCommands import devCommand



@slash.slash(
    name="registerServer",
    description="Make tournament helper feel welcome on your server.",
    guild_ids = botGuilds
)
@adminCommand
async def slashRegisterServer(ctx:SlashContext):
    guildId = ctx.guild_id
    if guildId is None:
        await ctx.send(strs.SpanishStrs.CANT_REGISTER_DM)
        return
    if serverController.getServer(guildId) is not None:
        await ctx.send(strs.SpanishStrs.SERVER_ALREADY_IN)
        return
    server = Server(serverId=guildId)
    if serverController.addServer(server):
        await ctx.send(strs.SpanishStrs.SERVER_REGISTERED)
    else:
        await ctx.send(strs.SpanishStrs.DB_UPLOAD_ERROR)


