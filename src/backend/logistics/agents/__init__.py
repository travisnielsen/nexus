"""
Agents package for the CopilotKit + Microsoft Agent Framework API.

Contains:
- logistics_agent.py: Logistics dashboard agent with flight payload tools
"""

from agents.logistics_agent import create_logistics_agent, ensure_foundry_agent_exists

__all__ = ["create_logistics_agent", "ensure_foundry_agent_exists"]
