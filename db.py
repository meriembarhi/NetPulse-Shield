from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class Alert(Base):
    __tablename__ = 'alerts'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    anomaly_score = Column(Float)
    is_anomaly = Column(Boolean)
    severity = Column(String(10), default='medium')
    status = Column(String(20), default='new')
    feature_json = Column(Text)
    advice = Column(Text, nullable=True)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer)
    action = Column(String(50))
    actor = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)
    note = Column(Text, nullable=True)

def get_engine(db_path: str = 'sqlite:///alerts.db'):
    return create_engine(db_path, connect_args={"check_same_thread": False})

def create_db(db_path: str = 'sqlite:///alerts.db'):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine

def get_session(db_path: str = 'sqlite:///alerts.db'):
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session()

def alert_from_row(row):
    # row is a pandas Series
    features = {}
    for k, v in row.items():
        try:
            json.dumps(v)
            features[k] = v
        except Exception:
            # non-serialisable values are converted to strings
            features[k] = str(v)
    return Alert(
        anomaly_score=float(row.get('anomaly_score', 0.0)),
        is_anomaly=bool(row.get('is_anomaly', False)),
        severity='high' if float(row.get('anomaly_score', 0.0)) < 0 else 'medium',
        feature_json=json.dumps(features),
    )

def persist_alerts_from_df(df, db_path: str = 'sqlite:///alerts.db'):
    engine = create_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()

    inserted = 0
    for _, row in df.iterrows():
        a = alert_from_row(row)
        session.add(a)
        inserted += 1
    session.commit()
    session.close()
    return inserted
