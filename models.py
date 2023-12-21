import pydantic


class SchemaBase(pydantic.BaseModel):
    class Config:
        from_attributes = True
        populate_by_name = True


class GosUser(SchemaBase):
    fullname: str
    lastname: str
    name: str
    patronymic: str
    sex: str
    dateBirthday: str

    codePassport: str  # 770-074
    inn: str
    datePassport: str
    placeBirthday: str

    numberPassport: str  # 6 numb 260231
    serialPassport: str  # 4 numb 4519
