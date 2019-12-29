import datetime
import decimal
import typing
import uuid

from dataclasses import dataclass


@dataclass
class Pet:
    animal: str
    name: str


@dataclass
class Person:
    id: uuid.UUID
    name: str
    email: str
    alive: bool
    phone: typing.List[str]
    weight: typing.Optional[float] = None
    birth_date: typing.Optional[datetime.date] = None
    movie_ratings: typing.Optional[typing.Dict[str, int]] = None

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


alice = Person(
    id=uuid.UUID('28ee3ae5-480b-46bd-9ae4-c61cf8341b95'),
    name='Alice',
    email='alice@example.com',
    alive=True,
    phone=['+31-6-1234-5678', '+31-20-123-4567'],
    weight=55.5,
    birth_date=datetime.date(1980, 4, 1),
    movie_ratings={'Star Wars': 8, 'Titanic': 4}
)

bob = Person(
    id=uuid.UUID('45805460-b90e-4b2e-a4ee-ef16de73feae'),
    name='Bob',
    email='bob@example.com',
    alive=False,
    phone=[],
)

charlie = Person(
    id=uuid.UUID('7dcdd6ef-a61b-4506-a2b0-0bfc9d23e9b5'),
    name='Charlie',
    email='charlie@xample.com',
    alive=True,
    phone=[]
)

alices_house = House(
    address='Abbey Road 123',
    owner=alice,
    residents=[charlie],
    room_area={'1st floor': {'kitchen': 50, 'living room': 10}, '2nd floor': {'bedroom': 20}}
)

abbey_road = Street(
    name='Abbey Road',
    length=decimal.Decimal('7.25'),
    houses={'123': alices_house}
)
