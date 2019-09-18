import datetime
import decimal
import typing

from dataclasses import dataclass


@dataclass
class Pet:
    animal: str
    name: str


@dataclass
class Person:
    name: str
    email: str
    alive: bool
    weight: typing.Optional[float]
    birth_date: typing.Optional[datetime.date]
    phone: typing.List[str]
    movie_ratings: typing.Optional[typing.Dict[str, int]]

    def age(self) -> int:
        return datetime.date(2020, 1, 1).year - self.birth_date.year if self.birth_date else None


@dataclass
class House:
    address: str
    owner: Person
    residents: typing.List[Person]
    room_area: typing.Dict[str, typing.Dict[str, int]]


@dataclass
class Street:
    name: str
    length: decimal.Decimal
    houses: typing.Dict[str, House]
