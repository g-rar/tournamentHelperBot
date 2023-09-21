from dataclasses import asdict, dataclass, field

from interactions import Embed
from models.tournamentModels import Tournament
from models.registrationModels import Participant, ParticipantRegistrationError
from typing import List

from utils.utils import OptionTypes

from baseModel import BaseModel
from models.registrationModels import RegistrationField

class BaseGameController:
    GAME:str = None
    WRONG_TYPE:int = 1
    REQUIRED_FIELD:int = 2
    ALREADY_REGISTERED:int = 3
    REGISTRATION_CLOSED:int = 4

    def __init__(self):
        self.PLAYER_FIELDS:list = list()
        self.TEAM_FIELDS:list = list()

    @staticmethod
    def getParticipantView(p:Participant):
        pDict = asdict(p)
        d = {k:v for k,v in pDict.items() if k in ["discordId", "discordDisplayname", "registeredTime"]}
        for field in p.fields:
            field:RegistrationField
            d[field.name] = field.value
        return d

    async def validateFields(self, fields:List[RegistrationField], tournament:Tournament, review:bool=False, override=False):
        newFields = []
        for field in fields:
            # if validation fails for some field throws error
            res = self.validateField(field, review)
            newFields.append(res[0])
        return (newFields, None)

    def validateField(self, field: RegistrationField, review:bool = False):
        ''' Validate that the value given in the field meets
        the field constraints'''
        try:
            t = self.getFieldType(field.fieldType)
            if field.value is None and field.required:
                raise ParticipantRegistrationError(field, BaseGameController.REQUIRED_FIELD)
            val = t(field.value)
            field.value = val
            return (field, True)
        except ValueError:
            raise ParticipantRegistrationError(f"Wrong value type for {field.name}: '{field.value}'",BaseGameController.WRONG_TYPE)
        except ParticipantRegistrationError as e:
            raise e

    async def checkParticipants(self, participants: List[Participant], tournament):
        newParticipants = []
        failed = []
        for participant in participants:
            try:
                newFields, playerData = await self.validateFields(participant.fields, tournament, review=True)
                participant.playerData = playerData
                participant.fields = newFields
                newParticipants.append(participant)
            except Exception as e:
                failed.append((participant, str(e)))
        return newParticipants, failed
            
    def getFieldType(self, fieldType: int) -> type:
        if fieldType == OptionTypes.STRING:
            return str
        elif fieldType == OptionTypes.INTEGER:
            return int
        elif fieldType == OptionTypes.BOOLEAN:
            return bool
        else:
            return None
    
    def addFieldsToEmbed(self, embed:Embed, tournament:Tournament, lang:str):
        pass

@dataclass
class BasePlayer:
    game:str = None
    warnings: list[str] = field(default_factory=list)

    @staticmethod
    def fromDict(d):
        return BaseModel.fromDict(d, BasePlayer)
