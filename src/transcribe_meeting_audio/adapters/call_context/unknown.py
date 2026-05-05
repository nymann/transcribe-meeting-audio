from transcribe_meeting_audio.domain.meeting import CallApp


class UnknownCallContext:
    """Stub: always reports UNKNOWN until process detection lands."""

    def identify(self) -> CallApp:
        return CallApp.UNKNOWN
