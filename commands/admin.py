from controllers.admin import adminCommand
from discord_slash.utils.manage_commands import create_option

import strings as strs
from utils import OptionTypes

import discord
from discord_slash.context import SlashContext

from bot import slash, botGuilds
from controllers.server import serverController
from devCommands.devCommands import devCommand


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
async def addOperatorRole(ctx:SlashContext, role:discord.Role):
    if ctx.guild_id is None:
        await ctx.send(strs.SpanishStrs.NOT_FOR_DM)
        return
    server = serverController.getServer(ctx.guild_id, upsert=True)
    if not server:
        await ctx.send(strs.SpanishStrs.DB_UPLOAD_ERROR)
        return
    server.adminRoles.append(role.id)
    res = serverController.updateServer(server)
    if res:
        await ctx.send(strs.SpanishStrs.ADDED_OPERATOR_ROLE.format(role=role.name))
        if len(role.members) > 10:
            await ctx.send(strs.SpanishStrs.MANY_PEOPLE_WITH_ROLE.format(rolecount=len(role.members)))
        return
    else:
        await ctx.send(strs.SpanishStrs.DB_UPLOAD_ERROR)
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
async def removeOperatorRole(ctx:SlashContext, role:discord.Role):
    if ctx.guild_id is None:
        await ctx.send(strs.SpanishStrs.NOT_FOR_DM)
        return
    server = serverController.getServer(ctx.guild_id)
    if not server:
        await ctx.send(strs.SpanishStrs.NO_OPERATOR_ROLES)
        return
    if role.id not in server.adminRoles:
        await ctx.send(strs.SpanishStrs.NOT_AN_OPERATOR_ROLE.format(role=role.name))
        return
    server.adminRoles.remove(role.id)
    res = serverController.updateServer(server)
    if res:
        await ctx.send(strs.SpanishStrs.REMOVED_OPERATOR_ROLE.format(role=role.name))
        return
    else:
        await ctx.send(strs.SpanishStrs.DB_UPLOAD_ERROR)
        return