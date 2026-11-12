"""SQLAlchemy database models for UAV-QAOA-SAR."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.types import JSON

from backend.db.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class OptimizationRun(Base):
    """Stores the execution snapshot of an optimization run for history and comparison."""
    __tablename__ = "optimization_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(String(36), unique=True, index=True, nullable=False, default=generate_uuid)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    scenario_name = Column(String(100), nullable=False, index=True)
    solver_name = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="completed")  # completed, failed, no_feasible_solution
    request_data = Column(JSON, nullable=False)
    result_data = Column(JSON, nullable=False)
    selected_waypoint_count = Column(Integer, nullable=True)
    feasible = Column(Boolean, nullable=True)
    objective_value = Column(Float, nullable=True)
    runtime_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

