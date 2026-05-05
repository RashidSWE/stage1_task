from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, func
from db.session import get_session
from models.model import NameAnalysis, GenderCategory, GenderResult, AgeResult, NationalizeResult, NameRequest, ProfileResponse, Profile
from core.cache import cache_get, cache_set
from core.normalizer import normalize_filters, make_cache_key
from services.security import get_current_user, get_user_browser
from services.classify import classify_age
from services.parse import parse_query
from typing import Optional
import asyncio
import httpx
import pycountry

router = APIRouter()


@router.post("/profiles", status_code=status.HTTP_201_CREATED)
async def analyze(request: NameRequest, session: Session = Depends(get_session)):
    name = request.name.strip()
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
        raise HTTPException(status_code=504, detail="External API timed out")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Failed to reach external API")
    
    gender_data = gender_res.json()
    age_data = age_res.json()
    nat_data = nat_res.json()
    print(nat_data)
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
    country_object = pycountry.countries.get(alpha_2=top_country["country_id"])

    nationality = None

    if top_country:
        nationality = NationalizeResult(
            name_id=person.id,
            country_id=top_country["country_id"],
            country_probability=top_country["probability"],
            country_name=country_object.name if country_object else "Unknown"
        )
        session.add(nationality)
    print(nationality.country_name)
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
            "country_name": nationality.country_name if nationality else None,
            "created_at": person.created_at
        }
    }

def fetch_profiles(
    gender, age_group, country_id, min_age, max_age,
    min_gender_probability, min_country_probability,
    sort_by, order, page, limit, session
):
    query = select(Profile)
    normalized = normalize_filters(query)
    cache_key = make_cache_key(query)

    cached_result = cache_get(cache_key)

    if cached_result is not None:
        return {"status": "success", "count": len(cached_result), "data": cached_result, "cached": True}

    if gender:
        query = normalized.where(Profile.gender == gender.lower())
    if country_id:
        query = normalized.where(Profile.country_id == country_id.upper())
    if age_group:
        query = normalized.where(Profile.age_group == age_group.lower())
    if min_age is not None:
        query = normalized.where(Profile.age >= min_age)
    if max_age is not None:
        query = normalized.where(Profile.age <= max_age)
    if min_gender_probability is not None:
        query = normalized.where(Profile.gender_probability >= min_gender_probability)
    if min_country_probability is not None:
        query = normalized.where(Profile.country_probability >= min_country_probability)

    total = session.exec(select(func.count()).select_from(query.subquery())).one()

    if sort_by:
        column = getattr(Profile, sort_by)
        query = query.order_by(column.desc() if order == "desc" else column.asc())

    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    profiles = session.exec(query).all()

    result = [ProfileResponse.model_validate(p) for p in profiles]

    cache_set(cache_key, result)
    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": reesult,
        "cached": False
    }

@router.get("/profiles/search")
async def Natural_language_query(
    q: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_session)
):
    filters = parse_query(q)

    if filters is None:
        return {"status": "error", "messag": "Unable to interpret query"}

    return fetch_profiles(
        gender=filters.get("gender"),
        age_group=filters.get("age_group"),
        country_id=filters.get("country_id"),
        min_age=filters.get("min_age"),
        max_age=filters.get("max_age"),
        min_gender_probability=filters.get("min_gender_probability"),
        min_country_probability=filters.get("min_country_probability"),
        sort_by=filters.get("sort_by"),
        order=filters.get("order", "asc"),
        page=page,
        limit=limit,
        session=session
    )

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
    gender: Optional[str] = Query(None, description="male | female | unkown"),
    country_id: Optional[str] = Query(None, description="ISO code e.g US, UK"),
    age_group: Optional[str] =Query(None, description="child | teenager | adult| senior"),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    min_gender_probability: Optional[float] = Query(None),
    min_country_probability: Optional[float] = Query(None),

    sort_by: Optional[str] = Query(None, pattern="^(age|created_at|gender_probability)$"),
    order: Optional[str] = Query("asc", pattern="^(asc|desc)$"),

    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_session)
):
    
    # statement = (
    #     select(NameAnalysis, GenderResult, AgeResult, NationalizeResult)
    #     .join(GenderResult, GenderResult.name_id == NameAnalysis.id)
    #     .join(AgeResult, AgeResult.name_id == NameAnalysis.id)
    #     .join(NationalizeResult, NationalizeResult.name_id == NameAnalysis.id)
    # )

    # if gender:
    #     statement = statement.where(GenderResult.gender == gender.lower())
    # if country_id:
    #     statement = statement.where(NationalizeResult.country_id == country_id)
    # if age_group:
    #     statement = statement.where(AgeResult.age_group == age_group)
    
    # results = session.exec(statement).all()

    # data = []

    # for name, gender_res, age_res, nat_res in results:
    #     data.append({
    #         "id": name.id,
    #         "name": name.name,
    #         "gender": gender_res.gender,
    #         "age": age_res.age,
    #         "age_group": age_res.age_group,
    #         "country_id": nat_res.country_id,
    #     })
    
    return fetch_profiles(
        gender, age_group, country_id, min_age, max_age,
        min_gender_probability, min_country_probability,
        sort_by, order, page, limit, session
    )

@router.delete("/profiles/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(id: str, session: Session = Depends(get_session)):
    profile = session.get(NameAnalysis, id)

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    session.delete(profile)
    session.commit()

    return


@router.get("/Profile/me")
async def get_my_profile(user_id: str = Depends(get_current_user)):
    return {
        "message": "Authorization successful!",
        "username": user_id
    }

@router.get("/portal/dashboard")
async def get_secure_dashboard(user_id: str = Depends(get_user_browser)):
    return {
        "message": "Web Authorization successful!",
        "username": user_id,
        "secure_data": [
            {"id": 1, "resource": "Backend Architecture Diagrams", "access": "granted"},
            {"id": 2, "resource": "Database Credentials", "access": "granted"}
        ]
}
