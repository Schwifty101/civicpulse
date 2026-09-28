from app.config import Settings
from app.providers.triage.base import TriageProvider
from app.providers.triage.llm import LLMTriage
from app.providers.triage.ollama import OllamaTriage
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage


def build_triage_provider(settings: Settings) -> TriageProvider:
    match settings.triage_provider:
        case "llm":
            return LLMTriage(
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
                model=settings.groq_model,
            )
        case "ollama":
            return OllamaTriage(base_url=settings.ollama_base_url, model=settings.ollama_model)
        case "simulated":
            return SimulatedTriage()
        case "rules":
            return RuleBasedTriage()
        case other:
            raise ValueError(
                f"Unknown TRIAGE_PROVIDER={other!r}; expected one of "
                "rules|simulated|llm|ollama"
            )
