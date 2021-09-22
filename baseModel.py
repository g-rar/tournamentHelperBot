from dataclasses import dataclass, asdict, fields
from typing import Generic

@dataclass
class BaseModel:
    @staticmethod
    def fromDict(d:dict, c:type):
        instanceFields = {}
        f = {field.name:field.type for field in fields(c)}
        for key, val in d.items():
            if key in f.keys():
                if isinstance(f[key], type) and issubclass(f[key], BaseModel):
                    instanceFields[key] = f[key].fromDict(val)
                else:
                    instanceFields[key] = d[key]
        instance = c(**instanceFields)
        return instance