import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Available Tools:
1. **search_course_content**: Search for specific course content or detailed educational materials
2. **get_course_outline**: Get course structure including title, link, and complete lesson list

Tool Usage Guidelines:
- **Course outline questions** (e.g., "What does X course cover?", "What are the lessons in X?", "Show me the outline of X"): Use the `get_course_outline` tool
- **Course content questions** (e.g., "How do I do X?", "Explain Y from course Z"): Use the `search_course_content` tool
- **Up to two sequential tool calls per query** - use multiple tools when needed (e.g., first get course details, then search related content)
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol for Course Outlines:
- When returning course outline information, always include:
  - Course title
  - Course link
  - Complete lesson list as a numbered list with **bold lesson titles**
  - "Key topics included:" followed by a numbered list (brief, no sub-bullets)

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course-specific questions**: Use appropriate tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results" or "based on the tool results"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)
        
        # Return direct response
        return response.content[0].text
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls with support for sequential tool calling.

        Supports up to MAX_ROUNDS of sequential tool calls, allowing Claude to
        chain multiple tools (e.g., get_course_outline then search_course_content).

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        MAX_ROUNDS = 2
        messages = base_params["messages"].copy()
        current_response = initial_response
        round_count = 0

        while round_count < MAX_ROUNDS:
            round_count += 1

            # Add Claude's tool_use response to conversation
            messages.append({"role": "assistant", "content": current_response.content})

            # Execute all tool calls, collect results
            tool_results = []
            execution_failed = False
            for block in current_response.content:
                if block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(block.name, **block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True
                        })
                        execution_failed = True

            # Add tool results to conversation
            messages.append({"role": "user", "content": tool_results})

            # API call WITH tools (allows sequential tool calling)
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
                "tools": base_params.get("tools"),
                "tool_choice": {"type": "auto"}
            }
            current_response = self.client.messages.create(**next_params)

            # Check termination conditions
            if current_response.stop_reason != "tool_use":
                break  # Claude is done with tools
            if execution_failed:
                break  # Tool error, let Claude respond with error context

        # Extract and return final text
        return self._extract_text_response(current_response)

    def _extract_text_response(self, response) -> str:
        """Extract text content from a Claude response."""
        for block in response.content:
            if hasattr(block, 'text'):
                return block.text
        return ""