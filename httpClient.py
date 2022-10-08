from typing import List
from bot import httpClient
from interactions import Channel

async def getAllUsersFromReaction(channelId: int, messageId:int, emoji:str) -> List[dict]:
    reactions = await httpClient.get_reactions_of_emoji(
        channel_id=channelId, 
        message_id=messageId, 
        emoji=emoji,
        limit=100
    )
    i = 0
    added = 0
    if len(reactions) == 100:
        # loop until you get all of them
        while added == 100:
            new_reactions = await httpClient.get_reactions_of_emoji(
                channel_id=channelId, 
                message_id=messageId, 
                emoji=emoji,
                limit=100,
                after= (i:=i+1) * 100
            )
            added = len(new_reactions)
            reactions += new_reactions
    return reactions