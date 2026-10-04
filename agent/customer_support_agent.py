from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent.prompts import SYSTEM_PROMPT
from agent.state import AgentState
from config import settings
from tools.customer_tool import CustomerTool
from tools.email_tool import EmailTool
from tools.ticket_tool import TicketTool
from utils import configure_logging, log_agent_completed, log_agent_started, log_tool_requested


class CustomerSupportAgent:
    def __init__(self) -> None:
        configure_logging()
        self.tools = [
            CustomerTool().as_tool(),
            TicketTool().as_tool(),
            EmailTool().as_tool(),
        ]
        self.llm = self._build_llm()
        self.graph = self._build_graph()

    def _build_llm(self):
        if not settings.openai_api_key:
            return None

        kwargs = {
            "model": settings.openai_model,
            "api_key": settings.openai_api_key,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs).bind_tools(self.tools)

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("customer_support_agent", self._agent_node)
        graph.add_node("tools", ToolNode(self.tools))
        graph.add_edge(START, "customer_support_agent")
        graph.add_conditional_edges("customer_support_agent", tools_condition)
        graph.add_edge("tools", "customer_support_agent")
        return graph.compile()

    def _agent_node(self, state: AgentState) -> dict:
        messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        response = self.llm.invoke(messages)
        for tool_call in response.tool_calls:
            log_tool_requested(tool_call["name"])
        return {"messages": [response]}

    async def run(self, message: str) -> str:
        if self.llm is None:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        log_agent_started()
        result = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=message)]}
        )
        log_agent_completed()

        content = result["messages"][-1].content
        if isinstance(content, str):
            return content
        return str(content)
