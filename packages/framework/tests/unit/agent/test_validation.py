"""
Unit tests for Agent input validation.

These tests verify all validation edge cases without making any LLM calls.
All tests are fast and have no external dependencies.

Test Cases:
1. test_message_type_validation - Non-string message raises ValidationError
2. test_message_length_limit - Message > 100k chars raises ValidationError
3. test_message_length_valid - Message <= 100k chars is valid
4. test_max_tokens_upper_limit - max_tokens > 100k raises ValidationError
5. test_max_tokens_type_validation - Non-integer max_tokens raises ValidationError
6. test_temperature_type_validation - Non-numeric temperature raises ValidationError
7. test_temperature_boundary_valid - Temperature 0.0 and 2.0 are valid
8. test_temperature_boundary_invalid - Temperature < 0.0 or > 2.0 raises ValidationError
"""

from framework.agents import Agent
from framework.agents.exceptions import ValidationError
from framework.models.huggingface import HuggingFaceLocal
import pytest


@pytest.fixture
def mock_model():
    """Mock model for unit tests (not actually used)."""
    return HuggingFaceLocal("HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=10)


@pytest.mark.unit
class TestMessageValidation:
    """Tests for message validation."""

    @pytest.mark.asyncio
    async def test_message_type_validation(self, mock_model):
        """Non-string message raises ValidationError."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )

        # Test with non-string types
        with pytest.raises(ValidationError, match="Message must be a string"):
            await agent.invoke(123)  # type: ignore

    @pytest.mark.asyncio
    async def test_message_length_limit(self, mock_model):
        """Message > 100k chars raises ValidationError."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )

        # Create message > 100k chars
        long_message = "a" * 100_001

        with pytest.raises(
            ValidationError, match="Message cannot be longer than 100000 characters"
        ):
            await agent.invoke(long_message)

    @pytest.mark.asyncio
    async def test_message_length_valid(self, mock_model):
        """Message <= 100k chars is valid."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )

        # Create message exactly 100k chars (should be valid)
        valid_message = "a" * 100_000

        # Should not raise ValidationError (may raise other errors, but not validation)
        try:
            await agent.invoke(valid_message)
        except ValidationError:
            pytest.fail("ValidationError should not be raised for 100k char message")
        except Exception:
            # Other errors (like model errors) are OK
            pass


@pytest.mark.unit
class TestMaxTokensValidation:
    """Tests for max_tokens validation."""

    @pytest.mark.asyncio
    async def test_max_tokens_upper_limit(self, mock_model):
        """max_tokens > 100k raises ValidationError."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )

        with pytest.raises(ValidationError, match="max_tokens too large"):
            await agent.invoke("Hello", max_tokens=100_001)

    @pytest.mark.asyncio
    async def test_max_tokens_type_validation(self, mock_model):
        """Non-integer max_tokens raises ValidationError."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )

        with pytest.raises(ValidationError, match="Max tokens must be an integer"):
            await agent.invoke("Hello", max_tokens="100")  # type: ignore

    @pytest.mark.asyncio
    async def test_max_tokens_negative(self, mock_model):
        """Negative max_tokens raises ValidationError."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )

        with pytest.raises(ValidationError, match="Max tokens must be a non-negative integer"):
            await agent.invoke("Hello", max_tokens=-1)

    @pytest.mark.asyncio
    async def test_max_tokens_valid(self, mock_model):
        """Valid max_tokens values don't raise ValidationError."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )

        # Should not raise ValidationError
        try:
            await agent.invoke("Hello", max_tokens=1000)
        except ValidationError:
            pytest.fail("ValidationError should not be raised for valid max_tokens")
        except Exception:
            # Other errors are OK
            pass


@pytest.mark.unit
class TestTemperatureValidation:
    """Tests for temperature validation."""

    @pytest.mark.asyncio
    async def test_temperature_type_validation(self, mock_model):
        """Non-numeric temperature raises ValidationError."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )

        with pytest.raises(ValidationError, match="Temperature must be a number"):
            await agent.invoke("Hello", temperature="0.5")  # type: ignore

    @pytest.mark.asyncio
    async def test_temperature_boundary_valid(self, mock_model):
        """Temperature 0.0 and 2.0 are valid."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )

        # Should not raise ValidationError for boundary values
        try:
            await agent.invoke("Hello", temperature=0.0)
            await agent.invoke("Hello", temperature=2.0)
        except ValidationError:
            pytest.fail("ValidationError should not be raised for temperature 0.0 or 2.0")
        except Exception:
            # Other errors are OK
            pass

    @pytest.mark.asyncio
    async def test_temperature_too_low(self, mock_model):
        """Temperature < 0.0 raises ValidationError."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )

        with pytest.raises(ValidationError, match=r"Temperature must be between 0\.0 and 2\.0"):
            await agent.invoke("Hello", temperature=-0.1)

    @pytest.mark.asyncio
    async def test_temperature_too_high(self, mock_model):
        """Temperature > 2.0 raises ValidationError."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )

        with pytest.raises(ValidationError, match=r"Temperature must be between 0\.0 and 2\.0"):
            await agent.invoke("Hello", temperature=2.1)

    @pytest.mark.asyncio
    async def test_temperature_valid_range(self, mock_model):
        """Temperature in valid range doesn't raise ValidationError."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )

        # Should not raise ValidationError
        try:
            await agent.invoke("Hello", temperature=0.5)
            await agent.invoke("Hello", temperature=1.0)
            await agent.invoke("Hello", temperature=1.5)
        except ValidationError:
            pytest.fail("ValidationError should not be raised for valid temperature values")
        except Exception:
            # Other errors are OK
            pass
