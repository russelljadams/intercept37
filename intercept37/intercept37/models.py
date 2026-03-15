"""Database models for storing captured traffic."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

class CapturedRequest(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    method = Column(String(10), index=True)
    scheme = Column(String(10))
    host = Column(String(255), index=True)
    port = Column(Integer)
    path = Column(Text)
    query = Column(Text, nullable=True)
    request_headers = Column(Text)  # JSON
    request_body = Column(Text, nullable=True)
    status_code = Column(Integer, nullable=True, index=True)
    response_headers = Column(Text, nullable=True)  # JSON
    response_body = Column(Text, nullable=True)
    response_time = Column(Float, nullable=True)  # seconds
    content_type = Column(String(255), nullable=True)
    is_intercepted = Column(Boolean, default=False)
    tags = Column(Text, nullable=True)  # JSON array
    notes = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "method": self.method,
            "scheme": self.scheme,
            "host": self.host,
            "port": self.port,
            "path": self.path,
            "query": self.query,
            "url": f"{self.scheme}://{self.host}{self.path}{"?" + self.query if self.query else ""}",
            "request_headers": self.request_headers,
            "request_body": self.request_body,
            "status_code": self.status_code,
            "response_headers": self.response_headers,
            "response_body": self.response_body,
            "response_time": self.response_time,
            "content_type": self.content_type,
            "is_intercepted": self.is_intercepted,
            "tags": self.tags,
            "notes": self.notes,
        }

class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    vuln_type = Column(String(100), index=True)
    severity = Column(String(20), index=True)  # critical, high, medium, low, info
    title = Column(String(500))
    description = Column(Text)
    evidence = Column(Text, nullable=True)
    remediation = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "vuln_type": self.vuln_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "remediation": self.remediation,
        }
