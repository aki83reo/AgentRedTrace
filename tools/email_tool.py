from langchain_core.tools import StructuredTool

from utils import format_tool_result, log_tool_result


class EmailTool:
    def as_tool(self):
        """Expose simulated email as a LangChain tool."""
        return StructuredTool.from_function(self.send_email)

    def send_email(self, recipient: str, subject: str, body: str) -> str:
        """Simulate sending an email. Does not deliver a real email."""
        result = {
            "status": "sent",
            "recipient": recipient,
            "subject": subject,
            "body": body,
        }
        log_tool_result(result)
        return format_tool_result(result)
