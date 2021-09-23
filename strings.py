class utilStrs:
    UNEXISTING_GAME = '''```diff
🔎🤔 The game '{}' is not currently supported. Check if there was a typo. The currently supported games are:

{}
```'''
    UNEXISTING_COMMAND = '''```diff
- There is no '{}' command. The currently supported commands are:

{}
```'''
    WARNING = '''```fix
[ {} ]
```'''
    ERROR = '''```css
[ {} ]
```'''
    INFO = '''```ini
[ {} ]
```'''
    NORMAL = '```{}```'
    DIFF = '''```diff
{}
```'''
    JSON='''```json
{}    
```'''
    JS='''```js
{}    
```'''

class SpanishStrs:
    #Generales
    DB_UPLOAD_ERROR = "No se pudo añadir la información. Intenta en otro momento y si no llamá a g.rar"
    NOT_FOR_DM = "Este comando no se puede usar en DMs ( ´･･)ﾉ(._.`)"
    ADMIN_ONLY = "Este comando solo lo pueden usar administradores (ㆆ_ㆆ)ﾉ"
    VALUE_SHOULD_BE_DEC = "El valor para la opción '{option}' debe ser un número."
    VALUE_SHOULD_BE_TEXT_CHANNEL = "El valor para la opción '{option}' debe ser un canal de texto."
    MESSAGE_NOT_FOUND = "No se encontró el mensaje: {data}..."

    #Server
    CANT_REGISTER_DM = "Este no es un servidor. No uno que pueda registrar al menos ¯\\\_(ツ)_/¯"
    SERVER_ALREADY_IN = "Este serividor ya está registrado. No puedes estar más registrado de lo que ya estás ( ´･･)ﾉ(._.`)"
    SERVER_REGISTERED = "Gracias por recibirme en el server, espero ser de ayuda ( •̀ ω •́ )✧"
    ADDED_OPERATOR_ROLE = "Se ha añadido el rol '{role}' como operador de este servidor (＾u＾)ノ~"
    REMOVED_OPERATOR_ROLE = "Se ha quitado el rol '{role}' como operador de este servidor..."
    NO_OPERATOR_ROLES = "En este momento, no hay ningún rol de operador en el server (._. u)"
    MANY_PEOPLE_WITH_ROLE = "Esas son {rolecount} personas a quien se les podria echar la culpa si algo sale mal (´。＿。｀)・・・"
    NOT_AN_OPERATOR_ROLE = "El rol '{role}' no es un rol de operador (u •_•)"

    #Tournament
    TOURNAMENT_UNEXISTING = "No se ha encontrado ningún torneo con el nombre '{name}', asegúrate de que escribiste el nombre bien (._.`)・・・"
    TOURNAMENT_ADDED = "Se ha añadido el torneo '{name}' al servidor, van a ser emocionantes juegos de **{game}**! ヾ(^▽^*)"
    TOURNAMENT_EXISTS_ALREADY = "Ya hay un torneo con el nombre '{name}', deberías cambiarlo para que la gente no se confunda (#｀-_ゝ-)"
    REGISTRATION_OPEN_CHAT = "Se ha abierto el registro para el torneo {tournament} en el chat {chat}."
    REGISTRATION_CLOSED = "Se ha cerrado el registro para el torneo {tournament}."
    REGISTRATION_CLOSED_ALREADY = "El registro para el torneo '{tournament}' ya estaba cerrado."
    INPUT_CHECK_IN_REACTION = "Reacciona a este mensaje con el emoji con el que los jugadores hacen check in."
    NO_REACTION_IN_MSG = "Nadie ha reaccionado con '{reaction}' :thinking:..."