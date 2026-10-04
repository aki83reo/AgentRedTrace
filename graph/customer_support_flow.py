from langchain_core.messages import SystemMessage
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from graph.state import AgentState
from prompts.customer_support import SYSTEM_PROMPT
from security.authorization import AuthorizationGate, guard_tools
from utils import log_tool_requested


class CustomerSupportFlow:
    def __init__(self, llm, tools) -> None:
        """Store the model and tools, then compile the graph."""
        self.llm = llm
        self.gate = AuthorizationGate()
        self.tools = guard_tools(tools, self.gate)
        self.graph = self._build_graph()

    def _build_graph(self):
        """Connect the agent node to ToolNode until the model stops requesting tools."""
        graph = StateGraph(AgentState)
        graph.add_node("customer_support_agent", self._agent_node)
        graph.add_node("tools", ToolNode(self.tools))
        graph.add_edge(START, "customer_support_agent")
        graph.add_conditional_edges("customer_support_agent", tools_condition)
        graph.add_edge("tools", "customer_support_agent")
        return graph.compile()

    def _agent_node(self, state: AgentState) -> dict:
        """Call the model with the system prompt and record any tool it requests."""
        messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        response = self.llm.invoke(messages)
        for tool_call in response.tool_calls:
            log_tool_requested(tool_call["name"], tool_call["args"])
        return {"messages": [response]}
