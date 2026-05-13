from abc import ABC, abstractmethod


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> bytes:
        """Synthesize text to speech. Returns raw WAV bytes."""
        ...

    @abstractmethod
    def list_voices(self) -> list[str]:
        """Return all available voice IDs for this provider."""
        ...
