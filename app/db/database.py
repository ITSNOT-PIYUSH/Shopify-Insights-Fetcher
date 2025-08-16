"""
Database configuration and models using SQLAlchemy.
"""
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy setup
Base = declarative_base()
engine = None
SessionLocal = None


class InsightsRecordModel(Base):
    """SQLAlchemy model for storing insights records."""
    
    __tablename__ = "insights_records"
    
    id = Column(Integer, primary_key=True, index=True)
    store_url = Column(String(500), nullable=False, index=True)
    store_name = Column(String(200), nullable=True)
    insights_data = Column(JSON, nullable=False)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processing_time = Column(Float, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<InsightsRecord(id={self.id}, store_url='{self.store_url}', success={self.success})>"


def init_db() -> None:
    """Initialize database connection and create tables."""
    global engine, SessionLocal
    
    try:
        # Only initialize if we have database configuration
        if not settings.database_url and not all([settings.db_host, settings.db_user, settings.db_name]):
            logger.info("💾 Database not configured - running in memory mode")
            return
        
        # Create engine
        database_url = settings.mysql_url
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=settings.debug
        )
        
        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("💾 Database connected successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Don't raise exception - app should work without database
        engine = None
        SessionLocal = None


def get_db() -> Optional[Session]:
    """
    Get database session.
    
    Returns:
        Database session or None if database is not configured
    """
    if SessionLocal is None:
        return None
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_health() -> bool:
    """
    Check database health.
    
    Returns:
        True if database is healthy, False otherwise
    """
    if engine is None:
        return False
    
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def save_insights_record(
    store_url: str,
    store_name: Optional[str],
    insights_data: dict,
    processing_time: Optional[float] = None,
    success: bool = True,
    error_message: Optional[str] = None
) -> Optional[int]:
    """
    Save insights record to database.
    
    Args:
        store_url: The store URL
        store_name: The store name
        insights_data: The insights data as JSON
        processing_time: Processing time in seconds
        success: Whether the operation was successful
        error_message: Error message if any
        
    Returns:
        Record ID if saved successfully, None otherwise
    """
    if SessionLocal is None:
        # Silently skip if database is not configured - this is expected behavior
        return None
    
    db = SessionLocal()
    try:
        record = InsightsRecordModel(
            store_url=store_url,
            store_name=store_name,
            insights_data=insights_data,
            processing_time=processing_time,
            success=success,
            error_message=error_message
        )
        
        db.add(record)
        db.commit()
        db.refresh(record)
        
        logger.debug(f"Saved insights record with ID: {record.id}")
        return record.id
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to save insights record: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def get_insights_record(store_url: str) -> Optional[dict]:
    """
    Get the most recent insights record for a store.
    
    Args:
        store_url: The store URL to search for
        
    Returns:
        Insights data if found, None otherwise
    """
    if SessionLocal is None:
        return None
    
    db = SessionLocal()
    try:
        record = db.query(InsightsRecordModel)\
                   .filter(InsightsRecordModel.store_url == store_url)\
                   .filter(InsightsRecordModel.success == True)\
                   .order_by(InsightsRecordModel.scraped_at.desc())\
                   .first()
        
        if record:
            return record.insights_data
        
        return None
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to get insights record: {e}")
        return None
    finally:
        db.close()


def get_all_insights_records(limit: int = 100, offset: int = 0) -> list:
    """
    Get all insights records with pagination.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        List of insights records
    """
    if SessionLocal is None:
        return []
    
    db = SessionLocal()
    try:
        records = db.query(InsightsRecordModel)\
                   .order_by(InsightsRecordModel.scraped_at.desc())\
                   .offset(offset)\
                   .limit(limit)\
                   .all()
        
        return [
            {
                "id": record.id,
                "store_url": record.store_url,
                "store_name": record.store_name,
                "scraped_at": record.scraped_at,
                "processing_time": record.processing_time,
                "success": record.success,
                "insights_data": record.insights_data
            }
            for record in records
        ]
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to get insights records: {e}")
        return []
    finally:
        db.close()
