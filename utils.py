from typing import List
from pymongo.database import Database
from pymongo.cursor import Cursor
import re

def getQueryAsList(c:Cursor) -> list:
    ret = [val for val in c]
    return ret

def extractQuotedSubstrs(s) -> List[str]:
    patter = r'"([^"]*)"'

    matches = re.findall(patter, s)
    parts = re.split(patter, s)
    res = []

    for x in parts:
        if x in matches:
            res.append(x)
        else:
            res += x.split()

    return res


class OptionTypes:
    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    ANY = 9