from enum import Enum
from local.lang.utils import utilStrs

class SpanishStrs(Enum):
    #General
    DB_UPLOAD_ERROR = "No se pudo añadir la información. Intenta en otro momento y si no llamá a g.rar"
    DB_DROP_ERROR = "No se pudo remover la información. Intenta en otro momento y si no llamá a g.rar"
    ERROR = "Ocurrió un error: \n" + utilStrs.ERROR
    NOT_FOR_DM = "Este comando no se puede usar en DMs ( ´･･)ﾉ(._.`)"
    ADMIN_ONLY = "Este comando solo lo pueden usar administradores (ㆆ_ㆆ)ﾉ"
    VALUE_SHOULD_BE_DEC = "El valor para la opción `{option}` debe ser un número."
    VALUE_SHOULD_BE_TEXT_CHANNEL = "El valor para la opción `{option}` debe ser un canal de texto."
    MESSAGE_NOT_FOUND = "No se encontró el mensaje: {data}..."
    MEMBER_NOT_FOUND_BY_ID = "No se encontró el usuario con id: `{id}`"
    REACTION_TIMEOUT = "Se acabó el tiempo para reaccionar. Hay un límite de {time} segundos. Intenta de nuevo (＾v＾u)..."
    MAY_TAKE_LONG = "Esto podría durar un rato (＾v＾u)..."
    GAME = "Juego"
    CREATED_AT = "Creado el"
    REGISTRATION = "Registro"
    OPEN = "📝 Abierto"
    CLOSED = "❌ Cerrado"
    BMAC_MSG = "Si te gustaría apoyar a mi desarrollador o apoyar metas de características, cómprame un café: ☕😋 https://www.buymeacoffee.com/gerardolop"

    #Server
    CANT_REGISTER_DM = "Este no es un servidor. No uno que pueda registrar al menos ¯\\\_(ツ)_/¯"
    SERVER_ALREADY_IN = "Este serividor ya está registrado. No puedes estar más registrado de lo que ya estás ( ´･･)ﾉ(._.`)"
    SERVER_REGISTERED = "Gracias por recibirme en el server, espero ser de ayuda ( •̀ ω •́ )✧"
    SERVER_UPDATED = "¡La información del servidor se ha actualizado!"
    ADDED_OPERATOR_ROLE = "Se ha añadido el rol '{role}' como operador de este servidor (＾u＾)ノ~"
    REMOVED_OPERATOR_ROLE = "Se ha quitado el rol '{role}' como operador de este servidor..."
    OPERATOR_ROLE_ALREADY_EXISTS = "Ese rol '{role}' ya es un rol de operador para empezar (＾v＾u)..."
    NO_OPERATOR_ROLES = "En este momento, no hay ningún rol de operador en el server (._. u)"
    MANY_PEOPLE_WITH_ROLE = "Esas son {rolecount} personas a quien se les podria echar la culpa si algo sale mal (´。＿。｀)・・・"
    NOT_AN_OPERATOR_ROLE = "El rol '{role}' no es un rol de operador (u •_•)"
    NEED_MANAGE_ROLES = "Para eso necesito permiso para administrar roles. Mover mi rol más arriba en la jerarquía de roles también podría ayudar (＾v＾u)..."
    LANGUAGE_CHANGED = "Se ha cambiado el idioma a Español para este servidor. ¡Espero que nos entendamos bien!"
    CANT_ASSIGN_ROLE_TO_USER = "No se pudo asignar el rol `{role}` al usuario `{username}`. Revisa que tenga permiso para administrar roles, y tal vez la jerarquía de roles (＾v＾u)..."

    #Tournament
    TOURNAMENT_UNEXISTING = "No se ha encontrado ningún torneo con el nombre `{name}`, asegúrate de que escribiste el nombre bien (._.`)・・・"
    TOURNAMENT_ADDED = "Se ha añadido el torneo `{name}` al servidor, van a ser emocionantes juegos de **{game}**! ヾ(^▽^*)"
    TOURNAMENT_DELETED = "Se ha borrado el torneo `{name}` del servidor. Ojalá hayan más en el futuro (＾u＾)ノ~"
    TOURNAMENT_UPDATED = "Se ha actualizado el torneo `{name}`. ¡Siento que ahora está mejor! ヾ(^▽^*)~"
    TOURNAMENT_EXISTS_ALREADY = "Ya hay un torneo con el nombre `{name}`, deberías cambiarlo para que la gente no se confunda (#｀-_ゝ-)"
    TOURNAMENT_GAME_WRONG = "El torneo `{name}` no es del juego `{game}`. Asegurate de que se puso el juego correcto cuando se creó el torneo (´。＿。｀)・・・"
    INPUT_CHECK_IN_REACTION = "Reacciona a este mensaje con el emoji con el que los jugadores hacen check in."
    NO_REACTION_IN_MSG = "Nadie ha reaccionado con `{reaction}` :thinking:..."

    #Registration
    PLAYER_REGISTERED = "Se ha registrado a **{username}** en el torneo **{tournament}** ( •̀ ω •́ )✧"
    PARTICIPANT_UNEXISTING = "No se ha encontrado el participante `{username}` en el torneo **{tournament}** (u •_•)"
    PARTICIPANT_DELETED = "Se ha eliminado el participante `{username}` del torneo **{tournament}** ヾ(^▽^*)"
    PARTICIPANTS_DELETED = "Se han eliminado `{amount}` participantes:"
    PARTICIPANT_REGISTRATION_FAILED = "No se pudo registrar a `{name}` en el torneo `{tournament}`. Esta es la razón: `{reason}`"
    REGISTRATION_OPEN_CHAT = "Se ha abierto el registro para el torneo `{tournament}` en el chat {chat}."
    REGISTRATION_OPEN_ALREADY = "Ya el registro está abierto para el torneo `{tournament}` en el chat {chat}."
    REGISTRATION_CLOSED_MSG = "Se ha cerrado el registro para el torneo `{tournament}`."
    REGISTRATION_CLOSED_ALREADY = "El registro para el torneo `{tournament}` ya estaba cerrado."
    REG_CHANNEL_NOT_FOUND = "No pude encontrar el canal de registro para el torneo `{tournament}`. Voy a cerrar el registro para el torneo. Lo puedes volver a abrir en cualquier momento."
    PARTICIPANT_COUNT = "Cuenta de participantes"
    PARTICIPANT_HAS_WARNINGS = "El participante `{username}` tiene los siguientes warnings respecto al torneo `{tournament}`:\n"
    PARTICIPANT_REGISTRATION_MSG_LINK = "Puedes ver el mensaje de registro de `{username}` aquí: {msg_url}"
    PARTICIPANTS_ROLE_REMOVED = "También se le ha quitado el rol \"@{rolename}\" a los participantes descalificados."
    NO_PARTICIPANTS_IN_TOURNAMENT = "No hay participantes registrados en el torneo `{tournament}` ¯\\\_(ツ)_/¯"

    #Tetr.io
    UNEXISTING_TETRIORANK = "No existe el rango `{rank}` (._.`)・・・"
    TETRIORANKCAP_LOWERTHAN_RANKFLOOR = "El rank-cap `{rank_cap}` no puede ser menor que el rank-floor `{rank_floor}` (._.`)・・・"
    TETRIOTRCAP_LOWERTHAN_TRFLOOR = "El tr-cap `{tr_cap}` no puede ser menor que el tr-floor `{tr_floor}` (._.`)・・・"
    #Tetr.io warnings
    TETRIO_INACTIVE_FOR_A_WEEK = "Este jugador no ha jugado un juego de tetra league desde hace `{}` días."
    TETRIO_PROMOTION_INMINENT = "Este jugador pronto va a subir de rango a `{}` si gana su siguiente juego de TL."
    TETRIO_NEAR_PROMOTION = "Este jugador está cerca de subir de rango fuera del cap del torneo."
    TETRIO_PLAYER_DECAYING = "La desviación de rating (RD) de este jugador está aumentando."
    TETRIO_HIGH_RD = "Este jugador tiene una desviación de rating (RD) muy alta: `{}`." 

    #JStris+
    JSTRIS_PREDICTED_GLICKO = "This player's glicko was predicted based on sprint PB."
    