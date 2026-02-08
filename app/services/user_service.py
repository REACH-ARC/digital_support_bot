from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, UserType, Agent, AgentRole

class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_user_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self, 
        telegram_id: int, 
        username: str | None = None, 
        first_name: str | None = None,
        last_name: str | None = None,
        user_type: UserType = UserType.CUSTOMER
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            # Create User
            user = User(
                telegram_user_id=telegram_id, 
                username=username, 
                first_name=first_name,
                last_name=last_name,
                user_type=user_type.value
            )
            self.session.add(user)
            await self.session.flush() # Flush to get ID if needed for Agent
            
            # If Agent, create Agent profile
            if user_type == UserType.AGENT:
                agent = Agent(user_id=user.id, role=AgentRole.AGENT.value)
                self.session.add(agent)

            await self.session.commit()
            await self.session.refresh(user)
        else:
            # Update info if changed
            changed = False
            if user.username != username:
                user.username = username
                changed = True
            if user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if user.last_name != last_name:
                user.last_name = last_name
                changed = True
            
            # If we found a user who should be an agent but isn't marked as one (e.g. promoted?)
            # For simplicity, we assume role doesn't change automatically to Agent via this method.
            # But if we wanted to ensuring they have an Agent profile:
            # if user_type == UserType.AGENT and not await self.get_agent_profile(user.id): ...
            
            if changed:
                await self.session.commit()
                
        return user
