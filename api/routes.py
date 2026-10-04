from fastapi import APIRouter, HTTPException

from agent.customer_support_agent import CustomerSupportAgent
from api.models import ChatRequest, ChatResponse

router = APIRouter()


class ChatAPI:
    def __init__(self) -> None:
        self.agent = CustomerSupportAgent()

    async def chat(self, request: ChatRequest) -> ChatResponse:
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
