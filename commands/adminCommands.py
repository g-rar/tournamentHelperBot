from datetime import datetime
from interactions import CommandContext, Option, OptionType, Role
import interactions
from controllers.adminContoller import adminCommand
from controllers.serverController import serverController
from contextExtentions.customContext import ServerContext, customContext
from local.names import StringsNames

from bot import bot, botGuilds

@bot.command(name="operators", scope=botGuilds)
async def operators(ctx:CommandContext): pass

@operators.subcommand(
    name="add_role",
    options=[
        Option(
            name="role", description="Role that will allow users to operate this bot as admin.",
            type=OptionType.ROLE, required=True
        )
    ]
)
@adminCommand
@customContext
async def addOperatorRole(ctx:CommandContext, scx: ServerContext, role:Role):
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    server = serverController.getServer(int(ctx.guild_id), upsert=True)
    if not server:
        await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)
        return
    if role.id in server.adminRoles:
        await scx.sendLocalized(StringsNames.OPERATOR_ROLE_ALREADY_EXISTS, role=role.name)
        return
    server.adminRoles.append(int(role.id))
    res = serverController.updateServer(server)
    if res:
        await scx.sendLocalized(StringsNames.ADDED_OPERATOR_ROLE, role=role.name)
        # TODO check how to get members from role
        # if len(role.members) > 10:
        #     await scx.sendLocalized(StringsNames.MANY_PEOPLE_WITH_ROLE, rolecount=len(role.members))
        return
    else:
        await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)
        return


@operators.subcommand(
    name="remove_role",
    options=[
        Option(
            name="role", description="Role that allows users to operate this bot as admin.",
            type=OptionType.ROLE, required=True
        )
    ]
)
@adminCommand
@customContext
async def removeOperatorRole(ctx:CommandContext, scx: ServerContext, role:Role):
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    server = serverController.getServer(int(ctx.guild_id))
    if not server or len(server.adminRoles) == 0:
        await scx.sendLocalized(StringsNames.NO_OPERATOR_ROLES)
        return
    if role.id not in server.adminRoles:
        await scx.sendLocalized(StringsNames.NOT_AN_OPERATOR_ROLE, role=role.name)
        return
    server.adminRoles.remove(int(role.id))
    res = serverController.updateServer(server)
    if res:
        await scx.sendLocalized(StringsNames.REMOVED_OPERATOR_ROLE, role=role.name)
        return
    else:
        await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)
        return

@operators.subcommand(
    name="list_roles"
)
@adminCommand
@customContext
async def listOperatorRoles(ctx:CommandContext, scx:ServerContext):
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    server = serverController.getServer(int(ctx.guild_id))
    if len(server.adminRoles) == 0:
        ctx.channel.send("This server has no operator roles")
    roles = list(filter(
        lambda x: int(x.id) in server.adminRoles, 
        ctx.guild.roles
    ))
    rolesStr = "\n  -  " + "\n  -  ".join(list(map(lambda r: f"`@{r.name}`", roles)))
    embed  = interactions.Embed(
        title=f"Operator roles for {ctx.guild.name}:\n",
        description=rolesStr,
        color=0xFFBA00,
        timestamp=datetime.utcnow()
    )
    await ctx.send(embeds=[embed])

