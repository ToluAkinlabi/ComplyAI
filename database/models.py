# Add: database/models.py
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ComplianceReport(Base):
    __tablename__ = "compliance_reports"
    
    id = Column(Integer, primary_key=True)
    client_name = Column(String(100), nullable=False)
    document_name = Column(String(255), nullable=False)
    report_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer)
    processing_time = Column(Integer)  # in seconds