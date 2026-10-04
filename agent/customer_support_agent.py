from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from config import settings
from graph.customer_support_flow import CustomerSupportFlow
from tools.customer_tool import CustomerTool
from tools.email_tool import EmailTool
from tools.ticket_tool import TicketTool
from utils import configure_logging, log_agent_completed, log_agent_started


class CustomerSupportAgent:
    def __init__(self) -> None:
        """Prepare the tools, the chat model, and the LangGraph flow."""
        configure_logging()
        self.tools = [
            CustomerTool().as_tool(),
            TicketTool().as_tool(),
            EmailTool().as_tool(),
        ]
        self.llm = self._build_llm()
        self.flow = CustomerSupportFlow(self.llm, self.tools)
        self.messages = []

    def _build_llm(self):
        """Create the chat model and bind the tools so one tool runs at a time."""
        if not settings.openai_api_key:
            return None

        kwargs = {
            "model": settings.openai_model,
            "api_key": settings.openai_api_key,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs).bind_tools(
            self.tools,
            parallel_tool_calls=False,
        )

    async def run(self, message: str) -> str:
        """Run one user message through the graph and return the final text."""
        if self.llm is None:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        log_agent_started()
        result = await self.flow.graph.ainvoke(
            {"messages": [HumanMessage(content=message)]}
        )
        self.messages = result["messages"]
        content = result["messages"][-1].content
        if not isinstance(content, str):
            content = str(content)
        log_agent_completed(content)
        return content
