import json
import re
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


SIGNAL_SCHEMA = {
    "action": "BUY | SELL | HOLD",
    "confidence": "0.0 to 1.0",
    "reasoning": "2-4 Sätze Begründung",
    "key_metrics": {"metric_name": "value"},
    "risk_flags": ["Liste von Risiken, kann leer sein"],
    "time_horizon": "short | medium | long",
}

SKIP_SIGNAL = {
    "action": "HOLD",
    "confidence": 0.0,
    "reasoning": "",
    "key_metrics": {},
    "risk_flags": [],
    "time_horizon": "medium",
}


class BaseAgent:
    name: str = "base"
    system_prompt: str = ""

    def _call_claude(self, user_prompt: str) -> dict:
        client = get_client()

        schema_block = f"\n\nAntworte AUSSCHLIESSLICH mit diesem JSON-Schema (kein Text davor/danach):\n{json.dumps(SIGNAL_SCHEMA, ensure_ascii=False, indent=2)}"

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.system_prompt + schema_block,
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            "text": user_prompt,
                        },
                    ],
                }
            ],
        )

        raw = response.content[0].text.strip()
        return self._parse_json(raw)

    def _parse_json(self, raw: str) -> dict:
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON object
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"Konnte JSON nicht parsen: {raw[:200]}")

    async def analyze(self, symbol: str, asset_type: str, **kwargs) -> dict:
        raise NotImplementedError
