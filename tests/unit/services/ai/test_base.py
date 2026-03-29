from app.services.ai.base import AIProvider, AIProviderConfig


class _DummyProvider(AIProvider):
    @property
    def name(self) -> str:
        return "dummy"

    @property
    def supports_vision(self) -> bool:
        return False

    @property
    def supports_json_mode(self) -> bool:
        return True

    async def complete(self, messages, vision_input=None) -> str:
        raise NotImplementedError

    async def complete_json(self, messages, vision_input=None, json_schema=None):
        raise NotImplementedError


def test_parse_json_response_recovers_nested_object_from_wrapped_text():
    provider = _DummyProvider(AIProviderConfig(api_key="test", model="dummy"))

    result = provider._parse_json_response(
        'prefix {"floor_plan_analysis": {"rooms": [{"name": "Kitchen"}]}, "vastu_score": 8} suffix'
    )

    assert result["floor_plan_analysis"]["rooms"][0]["name"] == "Kitchen"
    assert result["vastu_score"] == 8
