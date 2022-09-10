from dataclasses import asdict, dataclass
from models.tournamentModels import Tournament
from models.registrationModels import Participant, RegistrationError
from typing import List

from utils import OptionTypes

from baseModel import BaseModel
from models.registrationModels import RegistrationField

class BaseGameController:
    GAME:str = None
    WRONG_TYPE:int = 1
    REQUIRED_FIELD:int = 2
    ALREADY_REGISTERED:int = 3
    REGISTRATION_CLOSED:int = 4
    PLAYER_FIELDS:list = list()
    TEAM_FIELDS:list = list()

    def __init__(self):
        pass

    def getParticipantView(self, p:Participant):
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
                raise RegistrationError(field, BaseGameController.REQUIRED_FIELD)
            val = t(field.value)
            field.value = val
            return (field, True)
        except ValueError:
            raise RegistrationError(f"Wrong value type for {field.name}: '{field.value}'",BaseGameController.WRONG_TYPE)
        except RegistrationError as e:
            raise e

    async def checkParticipants(self, participants: List[Participant], tournament):
        newParticipants = []
        failed = []
        for participant in participants:
            try:
                newFields, playerData = self.validateFields(participant.fields, tournament, review=True)
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

@dataclass
class BasePlayer:
    game:str = None

    @staticmethod
    def fromDict(d):
        return BaseModel.fromDict(d, BasePlayer)
