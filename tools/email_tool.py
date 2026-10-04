from langchain_core.tools import StructuredTool

from utils import format_tool_result, log_tool_executed


class EmailTool:
    def as_tool(self):
        return StructuredTool.from_function(self.send_email)

    def send_email(self, recipient: str, subject: str, body: str) -> str:
        """Simulate sending an email. Does not deliver a real email."""
        log_tool_executed("send_email")
        result = {
            "status": "sent",
            "recipient": recipient,
            "subject": subject,
            "body": body,
        }
        return format_tool_result(result)
