from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.model import NameAnalysis, GenderCategory, GenderResult, AgeResult, NationalizeResult
import httpx
from app.services.classify import classify_age
from typing import Optional
import asyncio
import httpx

router = APIRouter()


@router.post("/profiles", status_code=status.HTTP_201_CREATED)
async def analyze(name: str, session: Session = Depends(get_session)):

    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Missing or Empty name")

    if name.strip().isdigit():
        raise HTTPException(status_code=422, detail="Invalid Type")

    statement = select(NameAnalysis).where(NameAnalysis.name == name)
    existing_person = session.exec(statement).first()
    if existing_person:
        gender = session.exec(select(GenderResult).where(GenderResult.name_id == existing_person.id)).first()
        age = session.exec(select(AgeResult).where(AgeResult.name_id == existing_person.id)).first()
        nationality = session.exec(select(NationalizeResult).where(NationalizeResult.name_id == existing_person.id)).first()

        return {
            "status":"success",
            "message": "Profile already exists",
            "data": {
                "id": existing_person.id,
                "name": existing_person.name,
                "gender": gender.gender if gender else None,
                "gender_probability": gender.probability if gender else None,
                "sample_size": gender.count if gender else None,
                "age": age.age if age else None,
                "age_group": age.age_group if age else None,
                "country_id": nationality.country_id if nationality else None,
                "country_probability": nationality.country_probability if nationality else None,
                "created_at": existing_person.created_at
            },
        }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            gender_res, age_res, nat_res = await asyncio.gather(
                client.get(f"https://api.genderize.io?name={name}"),
                client.get(f"https://api.agify.io?name={name}"),
                client.get(f"https://api.nationalize.io?name={name}"),
            )
    except httpx.TimeoutException:
        raise HTTPException(status_c0de=504, detail="External API timed out")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Failed to reach external API")
    
    gender_data = gender_res.json()
    age_data = age_res.json()
    nat_data = nat_res.json()

    if not gender_data.get("gender") or not gender_data.get("count"):
        raise HTTPException(status_code=502, detail="Genderize returned an invalid response")

    if age_data.get("age") is None:
        raise HTTPException(status_code=502, detail="Agify returned an invalid response")

    if not nat_data.get("country"):
        raise HTTPException(status_code=502, detail="Nationalize returned and invalid response")

    person = NameAnalysis(name=name)
    session.add(person)
    session.flush()
    session.refresh(person)

    # Gender
    gender = GenderResult(
        name_id=person.id,
        gender=gender_data.get("gender", "unknown"),
        probability=gender_data.get("probability", 0),
        count=gender_data.get("count", 0)
    )

    age_value = age_data.get("age", 0)
    age = AgeResult(
        name_id=person.id,
        age=age_value,
        age_group=classify_age(age_value)
    )


    countries = nat_data.get("country", [])

    top_country = max(countries, key=lambda x: x["probability"], default=None)

    nationality = None

    if top_country:
        nationality = NationalizeResult(
            name_id=person.id,
            country_id=top_country["country_id"],
            country_probability=top_country["probability"],
        )
        session.add(nationality)

    session.add(gender)
    session.add(age)
    session.commit()

    return {
        "status": "success",
        "data": {
            "id": person.id,
            "name": name,
            "gender": gender.gender,
            "gender_probability": gender.probability,
            "sample_size": gender.count,
            "age": age.age,
            "age_group": age.age_group,
            "country_id": nationality.country_id if nationality else None,
            "country_probability": nationality.country_probability if nationality else None,
            "created_at": person.created_at
        }
    }

@router.get("/profiles/{id}")
async def get_profiles(id: str, session: Session = Depends(get_session)):

    if not id:
        raise HTTPException(status_code=400, detail="Missing or Empty ID")

    statement = select(NameAnalysis).where(NameAnalysis.id == id)
    existing_person = session.exec(statement).first()

    if not existing_person:
        raise HTTPException(status_code=404, detail="Profile not found")

    gender = session.exec(select(GenderResult).where(GenderResult.name_id == existing_person.id)).first()
    age = session.exec(select(AgeResult).where(AgeResult.name_id == existing_person.id)).first()
    nationality = session.exec(select(NationalizeResult).where(NationalizeResult.name_id == existing_person.id)).first()

    return {
        "status": "success",
        "data": {
            "id": existing_person.id,
            "name": existing_person.name,
            "gender": gender.gender if gender else None,
            "gender_probability": gender.probability if gender else None,
            "sample_size": gender.count if gender else None,
            "age": age.age if age else None,
            "age_group": age.age_group if age else None,
            "country_id": nationality.country_id if nationality else None,
            "country_probability": nationality.country_probability if nationality else None,
            "created_at": existing_person.created_at
        },
    }

@router.get("/profiles")
async def get_all_profiles(
    gender: Optional[str] = None,
    country_id: Optional[str] = None,
    age_group: Optional[str] = None,
    session: Session = Depends(get_session)
):
    if gender:
        gender = gender.lower()
    if country_id:
        country_id = country_id.upper()
    if age_group:
        age_group = age_group.lower()
    
    statement = (
        select(NameAnalysis, GenderResult, AgeResult, NationalizeResult)
        .join(GenderResult, GenderResult.name_id == NameAnalysis.id)
        .join(AgeResult, AgeResult.name_id == NameAnalysis.id)
        .join(NationalizeResult, NationalizeResult.name_id == NameAnalysis.id)
    )

    if gender:
        statement = statement.where(GenderResult.gender == gender.lower())
    if country_id:
        statement = statement.where(NationalizeResult.country_id == country_id)
    if age_group:
        statement = statement.where(AgeResult.age_group == age_group)
    
    results = session.exec(statement).all()

    data = []

    for name, gender_res, age_res, nat_res in results:
        data.append({
            "id": name.id,
            "name": name.name,
            "gender": gender_res.gender,
            "age": age_res.age,
            "age_group": age_res.age_group,
            "country_id": nat_res.country_id,
        })
    
    return {
        "status": "success",
        "count": len(data),
        "data": data
    }

@router.delete("/profiles/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(id: str, session: Session = Depends(get_session)):
    profile = session.get(NameAnalysis, id)

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    session.delete(profile)
    session.commit()

    return
