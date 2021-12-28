from controllers.adminContoller import adminCommand
from controllers.serverController import serverController
from discord_slash.utils.manage_commands import create_option
from local.localContext import CustomContext, localized
from local.names import StringsNames

from utils import OptionTypes

import discord

from bot import slash, botGuilds


@slash.subcommand(
    base="operators",
    name="add_role",
    guild_ids=botGuilds,
    options=[
        create_option(
            name="role", description="Role that will allow users to operate this bot as admin.",
            option_type=OptionTypes.ROLE, required=True
        )
    ]
)
@adminCommand
@localized
async def addOperatorRole(ctx:CustomContext, role:discord.Role):
    if ctx.guild_id is None:
        await ctx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    server = serverController.getServer(ctx.guild_id, upsert=True)
    if not server:
        await ctx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)
        return
    if role.id in server.adminRoles:
        await ctx.sendLocalized(StringsNames.OPERATOR_ROLE_ALREADY_EXISTS, role=role.name)
        return
    server.adminRoles.append(role.id)
    res = serverController.updateServer(server)
    if res:
        await ctx.sendLocalized(StringsNames.ADDED_OPERATOR_ROLE, role=role.name)
        if len(role.members) > 10:
            await ctx.sendLocalized(StringsNames.MANY_PEOPLE_WITH_ROLE, rolecount=len(role.members))
        return
    else:
        await ctx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)
        return


@slash.subcommand(
    base="operators",
    name="remove_role",
    guild_ids=botGuilds,
    options=[
        create_option(
            name="role", description="Role that allows users to operate this bot as admin.",
            option_type=OptionTypes.ROLE, required=True
        )
    ]
)
@adminCommand
@localized
async def removeOperatorRole(ctx:CustomContext, role:discord.Role):
    if ctx.guild_id is None:
        await ctx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    server = serverController.getServer(ctx.guild_id)
    if not server or len(server.adminRoles) == 0:
        await ctx.sendLocalized(StringsNames.NO_OPERATOR_ROLES)
        return
    if role.id not in server.adminRoles:
        await ctx.sendLocalized(StringsNames.NOT_AN_OPERATOR_ROLE, role=role.name)
        return
    server.adminRoles.remove(role.id)
    res = serverController.updateServer(server)
    if res:
        await ctx.sendLocalized(StringsNames.REMOVED_OPERATOR_ROLE, role=role.name)
        return
    else:
        await ctx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)
        return