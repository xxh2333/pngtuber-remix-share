from ninja import Schema


class RegisterIn(Schema):
    username: str
    password: str


class LoginIn(Schema):
    username: str
    password: str


class TokenOut(Schema):
    access: str
    refresh: str


class UserOut(Schema):
    id: int
    username: str
