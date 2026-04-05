from pydantic import BaseModel


class Config(BaseModel):
    url: str
    path: str = "data"
    port: int = 7890
    allow_lan: bool = False
    api_port: int = 9090
    secret: str = ""
