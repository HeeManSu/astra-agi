from framework.agents.tool import tool

def test_tool_hil_metadata():
    """Test that HIL metadata is stored in tool."""
    
    @tool(requires_approval=True)
    def delete_file(path: str) -> None:
        """Delete a file."""
        pass
    
    assert delete_file.requires_approval is True
    assert delete_file.external_execution is False
    assert delete_file.suspend_schema is None


def test_tool_external_execution():
    """Test external execution flag."""
    
    @tool(external_execution=True)
    def run_shell(command: str) -> str:
        """Run shell command."""
        return "executed"
    
    assert run_shell.external_execution is True
    assert run_shell.requires_approval is False


def test_tool_suspend_schema():
    """Test suspend schema metadata."""
    
    @tool(suspend_schema={"otp": str, "amount": float})
    def verify_payment(amount: float) -> bool:
        """Verify payment."""
        return True
    
    assert verify_payment.suspend_schema == {"otp": str, "amount": float}
    assert verify_payment.requires_approval is False
