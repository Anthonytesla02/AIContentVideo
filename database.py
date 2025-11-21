import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class VideoHistory(Base):
    __tablename__ = "video_history"
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, nullable=False)
    orientation = Column(String, nullable=False)
    length = Column(String, nullable=False)
    style = Column(String, nullable=False)
    video_path = Column(String, nullable=False)
    script_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    elevenlabs_chars = Column(Integer, default=0)
    replicate_calls = Column(Integer, default=0)
    pexels_calls = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_video_to_history(topic: str, orientation: str, length: str, style: str,
                          video_path: str, script_json: str, costs: dict):
    db = SessionLocal()
    try:
        video = VideoHistory(
            topic=topic,
            orientation=orientation,
            length=length,
            style=style,
            video_path=video_path,
            script_json=script_json,
            elevenlabs_chars=costs.get("elevenlabs_chars", 0),
            replicate_calls=costs.get("replicate_calls", 0),
            pexels_calls=costs.get("pexels_calls", 0),
            total_cost_usd=costs.get("total_cost_usd", 0.0)
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        return video.id
    finally:
        db.close()


def get_all_videos():
    db = SessionLocal()
    try:
        return db.query(VideoHistory).order_by(VideoHistory.created_at.desc()).all()
    finally:
        db.close()


def get_video_by_id(video_id: int):
    db = SessionLocal()
    try:
        return db.query(VideoHistory).filter(VideoHistory.id == video_id).first()
    finally:
        db.close()


def get_total_costs():
    db = SessionLocal()
    try:
        videos = db.query(VideoHistory).all()
        total_chars = sum(v.elevenlabs_chars for v in videos)
        total_replicate = sum(v.replicate_calls for v in videos)
        total_pexels = sum(v.pexels_calls for v in videos)
        total_cost = sum(v.total_cost_usd for v in videos)
        
        return {
            "total_chars": total_chars,
            "total_replicate": total_replicate,
            "total_pexels": total_pexels,
            "total_cost": total_cost,
            "total_videos": len(videos)
        }
    finally:
        db.close()
