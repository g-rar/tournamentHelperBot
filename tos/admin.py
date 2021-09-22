from dataclasses import dataclass
from dataclasses import field, asdict

from pymongo.collection import Collection
from pymongo.database import Database
from bson.objectid import ObjectId

import strings as strs
from utils import getQueryAsList

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord_slash.context import SlashContext
from baseModel import BaseModel

from bot import db, bot, slash, CONF
from tos.server import serverController
from devCommands.devCommands import devCommand



class AdminController:

    def isAdmin(server:discord.Guild,user:discord.Member) -> bool:
        if user.guild_permissions.administrator:
            return True
        serverObj = serverController.getServer(server.id)
        if not serverObj:
            return False
        if user.id in serverObj.adminUsers:
            return True
        if any(role in user.roles for role in serverObj.adminRoles):
            return True
        return False

# adminController = AdminController()

def adminCommand(f):
    async def wrapper(ctx: SlashContext, *args, **kargs):
        if AdminController.isAdmin(ctx.guild,ctx.author):
            await f(ctx, *args, **kargs)
        else:
            await ctx.send(strs.utilStrs.ERROR.format(strs.SpanishStrs.ADMIN_ONLY), hidden=True)
        return f
    return wrapper
