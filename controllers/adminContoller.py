from local.lang.eng import EnglishStrs
from local.lang.utils import utilStrs

import discord
from discord_slash.context import SlashContext

from controllers.serverController import serverController



class AdminController:

    def isAdmin(server:discord.Guild,user:discord.Member) -> bool:
        if user.guild_permissions.administrator:
            return True
        serverObj = serverController.getServer(server.id)
        if not serverObj:
            return False
        if user.id in serverObj.adminUsers:
            return True
        if any(role.id in serverObj.adminRoles for role in user.roles):
            return True
        return False

# adminController = AdminController()

def adminCommand(f):
    async def wrapper(ctx: SlashContext, *args, **kargs):
        if AdminController.isAdmin(ctx.guild,ctx.author):
            await f(ctx, *args, **kargs)
        else:
            await ctx.send(utilStrs.ERROR.format(EnglishStrs.ADMIN_ONLY.value), hidden=True)
        return f
    return wrapper
