"""Offline tests for the dropped-tool-call retry in tau2.utils.llm_utils.generate."""

import litellm

import tau2.utils.llm_utils as llm_utils
from tau2.data_model.message import SystemMessage, UserMessage
from tau2.environment.tool import as_tool


def _square(x: int) -> int:
    """Square a number.
        Args:
        x (int): The number.
    Returns:
        int: The square.
    """
    return x * x


def _response(content=None, tool_call=None, completion_tokens=14):
    message = {"role": "assistant", "content": content}
    if tool_call:
        message["tool_calls"] = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": tool_call[0], "arguments": tool_call[1]},
            }
        ]
    return litellm.ModelResponse(
        model="openai/test-model",
        choices=[{"index": 0, "finish_reason": "stop", "message": message}],
        usage={
            "prompt_tokens": 100,
            "completion_tokens": completion_tokens,
            "total_tokens": 100 + completion_tokens,
        },
    )


MESSAGES = [
    SystemMessage(role="system", content="You are a helpful assistant."),
    UserMessage(role="user", content="What is the square of 5?"),
]


def _patch(monkeypatch, responses):
    calls = []

    def fake_completion(**kwargs):
        calls.append(kwargs["tool_choice"])
        return responses[len(calls) - 1]

    monkeypatch.setattr(llm_utils, "completion", fake_completion)
    monkeypatch.setattr(llm_utils, "_write_llm_log", lambda *a, **k: None)
    return calls


def test_empty_response_is_retried_with_required(monkeypatch):
    calls = _patch(
        monkeypatch, [_response(), _response(tool_call=("_square", '{"x": 5}'))]
    )
    msg = llm_utils.generate("openai/test-model", MESSAGES, tools=[as_tool(_square)])
    assert calls == ["auto", "required"]
    assert msg.tool_calls[0].name == "_square"
    assert msg.tool_calls[0].arguments == {"x": 5}
    assert msg.usage == {"prompt_tokens": 200, "completion_tokens": 28}
    assert msg.raw_data["empty_tool_retry"] is True


def test_text_response_is_not_retried(monkeypatch):
    calls = _patch(monkeypatch, [_response(content="25")])
    msg = llm_utils.generate("openai/test-model", MESSAGES, tools=[as_tool(_square)])
    assert calls == ["auto"]
    assert msg.content == "25"
    assert msg.raw_data["empty_tool_retry"] is False


def test_empty_response_without_tokens_is_not_retried(monkeypatch):
    calls = _patch(monkeypatch, [_response(completion_tokens=0)])
    llm_utils.generate("openai/test-model", MESSAGES, tools=[as_tool(_square)])
    assert calls == ["auto"]


def test_tool_call_leaked_as_text_is_retried(monkeypatch):
    calls = _patch(
        monkeypatch,
        [
            _response(content="_square(x=5)"),
            _response(tool_call=("_square", '{"x": 5}')),
        ],
    )
    msg = llm_utils.generate("openai/test-model", MESSAGES, tools=[as_tool(_square)])
    assert calls == ["auto", "required"]
    assert msg.tool_calls[0].name == "_square"
    assert msg.raw_data["empty_tool_retry"] is True


def test_text_naming_unknown_function_is_not_retried(monkeypatch):
    calls = _patch(monkeypatch, [_response(content="print(25)")])
    llm_utils.generate("openai/test-model", MESSAGES, tools=[as_tool(_square)])
    assert calls == ["auto"]
