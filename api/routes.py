from fastapi import APIRouter, HTTPException

from agent.customer_support_agent import CustomerSupportAgent
from api.models import ChatRequest, ChatResponse

router = APIRouter()


class ChatAPI:
    def __init__(self) -> None:
        """Create the customer support agent used by this API."""
        self.agent = CustomerSupportAgent()

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Pass the user message to the agent and return its reply."""
        try:
            result = await self.agent.run(request.message)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return ChatResponse(response=result)


chat_api = ChatAPI()
router.add_api_route(
    "/chat",
    chat_api.chat,
    methods=["POST"],
    response_model=ChatResponse,
)
