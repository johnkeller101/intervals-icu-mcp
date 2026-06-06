"""Tests for middleware module."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp.exceptions import ToolError

from intervals_icu_mcp.middleware import ConfigMiddleware


class TestConfigMiddleware:
    """Tests for ConfigMiddleware."""

    async def test_valid_credentials_injects_config(self):
        """Test middleware injects config when credentials are valid."""
        middleware = ConfigMiddleware()

        mock_context = MagicMock()
        mock_context.fastmcp_context = MagicMock()
        mock_context.fastmcp_context.set_state = AsyncMock()

        call_next = AsyncMock(return_value="result")

        with patch.dict(os.environ, {
            "INTERVALS_ICU_API_KEY": "valid_key_abc",
            "INTERVALS_ICU_ATHLETE_ID": "i999999",
        }):
            result = await middleware.on_call_tool(mock_context, call_next)

        assert result == "result"
        mock_context.fastmcp_context.set_state.assert_called_once()
        call_next.assert_called_once()

    async def test_invalid_credentials_raises_tool_error(self):
        """Test middleware raises ToolError when credentials are invalid."""
        middleware = ConfigMiddleware()

        mock_context = MagicMock()
        mock_context.fastmcp_context = MagicMock()
        mock_context.fastmcp_context.set_state = AsyncMock()

        call_next = AsyncMock()

        with patch.dict(os.environ, {
            "INTERVALS_ICU_API_KEY": "",
            "INTERVALS_ICU_ATHLETE_ID": "",
        }, clear=False):
            # Clear any existing values
            env_patch = {
                "INTERVALS_ICU_API_KEY": "",
                "INTERVALS_ICU_ATHLETE_ID": "",
            }
            with patch.dict(os.environ, env_patch):
                with pytest.raises(ToolError, match="credentials not configured"):
                    await middleware.on_call_tool(mock_context, call_next)

        call_next.assert_not_called()

    async def test_no_fastmcp_context(self):
        """Test middleware handles missing fastmcp_context."""
        middleware = ConfigMiddleware()

        mock_context = MagicMock()
        mock_context.fastmcp_context = None

        call_next = AsyncMock(return_value="result")

        with patch.dict(os.environ, {
            "INTERVALS_ICU_API_KEY": "valid_key_abc",
            "INTERVALS_ICU_ATHLETE_ID": "i999999",
        }):
            result = await middleware.on_call_tool(mock_context, call_next)

        assert result == "result"
        call_next.assert_called_once()
