from interactions import CommandContext, Member, Permissions
from local.lang.eng import EnglishStrs
from local.lang.utils import utilStrs

# import discord
# from discord_slash.context import SlashContext

from controllers.serverController import serverController



class AdminController:

    async def isAdmin(ctx: CommandContext) -> bool:
        if await ctx.has_permissions(Permissions.ADMINISTRATOR):
            return True
        serverObj = serverController.getServer(ctx.guild_id)
        user:Member = ctx.author
        if not serverObj:
            return False
        if user.id in serverObj.adminUsers:
            return True
        if any(role.id in serverObj.adminRoles for role in user.roles):
            return True
        return False

# adminController = AdminController()

def adminCommand(f):
    async def wrapper(ctx: CommandContext, *args, **kargs):
        if await AdminController.isAdmin(ctx):
            await f(ctx, *args, **kargs)
        else:
            await ctx.send(utilStrs.ERROR.format(EnglishStrs.ADMIN_ONLY.value), ephemeral=True)
        return f
    return wrapper
