import json
from pathlib import Path
from sqlmodel import Session, select
from app.db.session import engine
from app.models.model import Profile


BASE_DIR = Path(__file__).parent
JSON_PATH = BASE_DIR / "seed_profiles.json"

def seed_profiles():
    with open(JSON_PATH, "r") as file:
        data = json.load(file)
    
    profiles = data["profiles"]

    with Session(engine) as session:
        for profile_data in profiles:
            existing = session.exec(
                select(Profile).where(Profile.name == profile_data["name"])
            ).first()

            if existing:
                return
            
            profile = [
                Profile(**profile_data)
                for profile_data in data["profiles"]
            ]

            session.add_all(profiles)
        
        session.commit()
        print(f"seeded {len(profiles)} profiles successfully")