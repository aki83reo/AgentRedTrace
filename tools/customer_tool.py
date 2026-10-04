from langchain_core.tools import StructuredTool

from utils import format_tool_result, log_tool_executed

CUSTOMERS = {
    "C001": {
        "customer_id": "C001",
        "name": "Rahul Sharma",
        "email": "rahul@example.com",
        "account_type": "premium",
    },
    "C002": {
        "customer_id": "C002",
        "name": "Priya Nair",
        "email": "priya@example.com",
        "account_type": "standard",
    },
}


class CustomerTool:
    def as_tool(self):
        return StructuredTool.from_function(self.get_customer)

    def get_customer(self, customer_id: str) -> str:
        """Look up a customer by customer_id, such as C001."""
        log_tool_executed("get_customer")
        customer = CUSTOMERS.get(customer_id.strip().upper())
        if customer is None:
            return format_tool_result({"error": "Customer not found"})
        return format_tool_result(customer)
