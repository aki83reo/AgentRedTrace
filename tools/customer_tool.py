from langchain_core.tools import StructuredTool

from utils import format_tool_result, log_tool_result

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
        """Expose customer lookup as a LangChain tool."""
        return StructuredTool.from_function(self.get_customer)

    def get_customer(self, customer_id: str) -> str:
        """Look up a customer by customer_id, such as C001."""
        customer = CUSTOMERS.get(customer_id.strip().upper())
        payload = {"error": "Customer not found"} if customer is None else customer
        log_tool_result(payload)
        return format_tool_result(payload)
