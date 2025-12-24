import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to sys.path to import models and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.base import Base
from main import init_db, seed_demo_data, seed_existing_demo_tenant
from config import settings

def reseed():
    print("Starting database re-seeding to Neon...")
    
    # Ensure DATABASE_URL is set
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        sys.exit(1)
    
    print(f"Connecting to database...")
    engine = create_engine(db_url)
    
    # Drop all tables and recreate them
    print("Dropping and recreating schema...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Initialize session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("Initializing standard database records...")
        # We can't just call init_db() because it uses the engine from models.base
        # which might be initialized with a different DATABASE_URL if not set in env yet.
        # But since we're setting it via env, it should be fine.
        
        # Manually perform what init_db does but with our local db session
        from models.user import User
        from core.auth import get_password_hash
        
        platform_owner = db.query(User).filter(User.role == "platform_owner").first()
        if not platform_owner:
            platform_owner = User(
                email="admin@optria.io",
                username="admin",
                password_hash=get_password_hash("OptriA2024!"),
                role="platform_owner",
                full_name="Platform Administrator",
                full_name_ar="مدير المنصة",
                is_active=True
            )
            db.add(platform_owner)
            db.commit()
            print("Created platform owner: admin@optria.io / OptriA2024!")
        
        print("Seeding demo data...")
        seed_demo_data(db)
        seed_existing_demo_tenant(db)
        
        print("Database re-seeded successfully!")
    except Exception as e:
        print(f"ERROR: Seeding failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reseed()
