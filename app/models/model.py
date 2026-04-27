from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
from uuid6 import uuid7
from datetime import datetime
from sqlalchemy.orm import Mapped


class NameRequest(BaseModel):
    name: str

class GenderCategory(str, Enum):
    MALE = "male"
    FEMALE =  "female"
    UNKNOWN = "unknown"

class NameAnalysis(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid7()), primary_key=True)
    name: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    gender: Optional["GenderResult"] = Relationship(back_populates="name", sa_relationship_kwargs={"cascade": "all, delete"})
    age: Optional["AgeResult"] = Relationship(back_populates="name", sa_relationship_kwargs={"cascade": "all, delete"})
    created_at: datetime = Field(default_factory=datetime.utcnow)

    nationality: Mapped[List["NationalizeResult"]] = Relationship(back_populates="name", sa_relationship_kwargs={"cascade": "all, delete"})
  


class GenderResult(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid7()), primary_key=True)
    name_id: str = Field(foreign_key="nameanalysis.id")
    gender: GenderCategory
    probability: float
    count: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

    name: Optional[NameAnalysis] = Relationship(back_populates="gender")


class NationalizeResult(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid7()), primary_key=True)
    name_id: str = Field(foreign_key="nameanalysis.id")
    country_id: str
    country_probability: float
    country_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    name: Optional[NameAnalysis] = Relationship(back_populates="nationality")

class AgeResult(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid7()), primary_key=True)
    name_id: str = Field(foreign_key="nameanalysis.id")
    age: int
    age_group: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    name: Optional[NameAnalysis] = Relationship(back_populates="age")


class Profile(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid7()), primary_key=True)
    name: str = Field(index=True, unique=True)
    gender: GenderCategory
    gender_probability: float
    age: int
    age_group: str
    country_id: str = Field(max_length=2)
    country_name: str
    country_probability: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProfileResponse(BaseModel):
    id: str
    name: str
    gender: GenderCategory
    gender_probability: float
    age: int
    age_group: str
    country_id: str
    country_name: str
    country_probability: float
    created_at: datetime

    model_config = {"from_attributes": True}