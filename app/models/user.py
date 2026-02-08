import uuid
import enum
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Enum, String, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

# Enums matching schema CHECK constraints
class UserType(str, enum.Enum):
    CUSTOMER = "customer"
    AGENT = "agent"

class AgentRole(str, enum.Enum):
    ADMIN = "admin"
    AGENT = "agent"

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    user_type: Mapped[str] = mapped_column(String(10), nullable=False) # 'customer' or 'agent'
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())

    @property
    def full_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or "Unknown"

    # Constraints
    __table_args__ = (
        CheckConstraint("user_type IN ('customer', 'agent')", name='users_user_type_check'),
    )

    # Relationships
    agent_profile: Mapped["Agent"] = relationship("Agent", uselist=False, back_populates="user")

    def __repr__(self):
        return f"<User {self.id} (tg={self.telegram_user_id})>"

class Agent(Base):
    __tablename__ = "agents"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), server_default='agent', nullable=False)
    is_online: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'agent')", name='agents_role_check'),
    )

    user: Mapped["User"] = relationship("User", back_populates="agent_profile")
