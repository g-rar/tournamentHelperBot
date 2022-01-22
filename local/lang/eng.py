from enum import Enum
from local.lang.utils import utilStrs

class EnglishStrs(Enum):
    #Generales
    DB_UPLOAD_ERROR = "The information couldn't be added. Try again later or try to contact g.rar"
    DB_DROP_ERROR = "The information couldn't be removed. Try again later or try to contact g.rar"
    ERROR = "There was an error: \n" + utilStrs.ERROR
    NOT_FOR_DM = "This command can't be used in DMs ( ´･･)ﾉ(._.`)"
    ADMIN_ONLY = "Only operators for this bot can use this command (ㆆ_ㆆ)ﾉ"
    VALUE_SHOULD_BE_DEC = "The value for the option `{option}` must be a number."
    VALUE_SHOULD_BE_TEXT_CHANNEL = "The value for the option `{option}` must be a text channel."
    MESSAGE_NOT_FOUND = "Couldn't find message: {data}..."
    MEMBER_NOT_FOUND_BY_ID = "Couldn't find user with id: `{id}`"
    REACTION_TIMEOUT = "Time for reacting is over. There's  a {time} seconds limit. Try again (＾v＾u)..."
    MAY_TAKE_LONG = "This may take a while (＾v＾u)..."

    #Server
    CANT_REGISTER_DM = "This is not a server. Not one that can be registered anyways ¯\\\_(ツ)_/¯"
    SERVER_ALREADY_IN = "This server is already registered. You can't be registered anymore than you are already ( ´･･)ﾉ(._.`)"
    SERVER_REGISTERED = "Thanks for receiving me on your server, hope to be helpfull ( •̀ ω •́ )✧"
    SERVER_UPDATED = "The server's information was updated!"
    ADDED_OPERATOR_ROLE = "The role '{role}' was added as bot operator on this server (＾u＾)ノ~"
    REMOVED_OPERATOR_ROLE = "The role '{role}' was removed as bot operator on this server..."
    OPERATOR_ROLE_ALREADY_EXISTS = "The role '{role}' is an operator role already (＾v＾u)..."
    NO_OPERATOR_ROLES = "At this momment, there's no operator role on this server (._. u)"
    MANY_PEOPLE_WITH_ROLE = "Those are {rolecount} people who could be blamed if something goes wrong (´。＿。｀)・・・"
    NOT_AN_OPERATOR_ROLE = "The role '{role}' is not an operator role (u •_•)"
    NEED_MANAGE_ROLES = "For that I need permission to manage roles. Also moving my role higher in the hierarchy could help (＾v＾u)..."
    LANGUAGE_CHANGED = "The language for this server has been changed to English. We're up for having nice conversations!"
    CANT_ASSIGN_ROLE_TO_USER = "Couldn't assign the role `{role}` to the user `{username}`. Please check if I have permission to manage roles, also check the roles hierarchy (＾v＾u)..."

    #Tournament
    TOURNAMENT_UNEXISTING = "Couldn't find a tournament with the name `{name}`, check if you typed the name correctly (._.`)・・・"
    TOURNAMENT_ADDED = "The tournament `{name}` has been added to the server, hope to see some exciting **{game}** games! ヾ(^▽^*)"
    TOURNAMENT_DELETED = "The tournament `{name}` has been deleted from the server. Looking forward to more in the future (＾u＾)ノ~"
    TOURNAMENT_EXISTS_ALREADY = "There's already a tournament named `{name}`, you should change it so people don't get confused (#｀-_ゝ-)"
    INPUT_CHECK_IN_REACTION = "React to this message with the emoji that players use to check in."
    NO_REACTION_IN_MSG = "There's no one who reacted with {reaction} :thinking:..."

    #Registration
    PLAYER_REGISTERED = "There player **{username}** has been registered in the tournament **{tournament}** ( •̀ ω •́ )✧"
    PARTICIPANT_UNEXISTING = "Couldn't find the participant `{username}` in the tournament **{tournament}** (u •_•)"
    PARTICIPANT_DELETED = "Participant `{username}` has been deleted from the tournament **{tournament}** ヾ(^▽^*)"
    PARTICIPANTS_DELETED = "The following `{amount}` participants were deleted:"
    PARTICIPANT_REGISTRATION_FAILED = "No se pudo registrar a `{name}`. Esta es la razón: `{reason}`"
    REGISTRATION_OPEN_CHAT = "Sign ups for the tournament `{tournament}` are now open on the chat {chat}."
    REGISTRATION_OPEN_ALREADY = "Sign ups for the tournament `{tournament}` were already open on {chat}."
    REGISTRATION_CLOSED = "Sign ups for the tournament `{tournament}` have been closed."
    REGISTRATION_CLOSED_ALREADY = "Sign ups for the tournament `{tournament}` were closed already."
    REG_CHANNEL_NOT_FOUND = "I couldn't find the registration channel that was set up for the tournament `{tournament}`. I'm going to close sign ups for this tournament. You can reopen them at any time"
    PARTICIPANTS_ROLE_REMOVED = "The role \"@{rolename}\" was also removed from the disqualified servers."

    #Tetr.io
    UNEXISTING_TETRIORANK = "There's no `{rank}` rank (._.`)・・・"
    TETRIORANKCAP_LOWERTHAN_RANKFLOOR = "The rank-cap `{rank_cap}` can't be lower than the rank-floor `{rank_floor}` (._.`)・・・"
    TETRIOTRCAP_LOWERTHAN_TRFLOOR = "The tr-cap `{tr_cap}` can't be lower than the tr-floor `{tr_floor}` (._.`)・・・"