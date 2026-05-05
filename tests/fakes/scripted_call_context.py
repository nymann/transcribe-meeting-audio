from transcribe_meeting_audio.domain.meeting import CallApp


class ScriptedCallContext:
    """A test fake that returns whichever app it was told to identify."""

    def __init__(self, app: CallApp = CallApp.UNKNOWN) -> None:
        self._app = app

    def set(self, app: CallApp) -> None:
        self._app = app

    def identify(self) -> CallApp:
        return self._app
