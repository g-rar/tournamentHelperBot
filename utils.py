from typing import List
from pymongo.cursor import Cursor
import re
import asyncio
from interactions import Button, ButtonStyle
from interactions.ext.paginator import ButtonKind
import local.names as strs
from local.names import languages
import logging

paginatorButtons = {
        "first": Button(style=ButtonStyle.SUCCESS, label="↞"), 
        "prev": Button(style=ButtonStyle.SUCCESS, label="←"), 
        "index": Button(style=ButtonStyle.SECONDARY, label="-"), 
        "next": Button(style=ButtonStyle.SUCCESS, label="→"), 
        "last": Button(style=ButtonStyle.SUCCESS, label="↠")
    }


def getStr(s:str, language:str, **kwargs):
    if not hasattr(strs.StringsNames, s):
        return s
    language = strs.languages.get(language, strs.EnglishStrs)
    if s not in language.__members__:
        if s in strs.EnglishStrs.__members__:
            return strs.EnglishStrs[s].value
        else:
            return s
    s:str = language[s].value
    if kwargs:
        try:
            s = s.format(**kwargs)
        except Exception as e:
            logging.error(f"Error when getting string '{s}' with kwargs '{kwargs}': ", e)
    return s

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