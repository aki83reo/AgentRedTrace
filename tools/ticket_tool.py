from langchain_core.tools import StructuredTool

from utils import format_tool_result, generate_ticket_id, log_tool_executed


class TicketTool:
    def as_tool(self):
        return StructuredTool.from_function(self.create_ticket)

    def create_ticket(self, customer_id: str, issue: str) -> str:
        """Create a support ticket for a customer_id and an issue description."""
        log_tool_executed("create_ticket")
        ticket = {
            "ticket_id": generate_ticket_id(),
            "customer_id": customer_id,
            "issue": issue,
            "status": "created",
        }
        return format_tool_result(ticket)
