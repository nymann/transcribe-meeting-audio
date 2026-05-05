"""Maps recently-triggering bundle IDs into a CallApp label.

Reads `last_trigger_bundles` off the CoreAudio detector — the same instance
that just emitted STARTED — so the label reflects the actual process that
opened the mic, not just whatever app happens to be running.
"""
from transcribe_meeting_audio.adapters.event_source.coreaudio_mic import (
    CoreAudioMicDetector,
)
from transcribe_meeting_audio.domain.meeting import CallApp


_BUNDLE_PREFIX_TO_APP: tuple[tuple[str, CallApp], ...] = (
    ("com.microsoft.teams", CallApp.TEAMS),
    ("com.microsoft.Teams", CallApp.TEAMS),
    ("us.zoom", CallApp.ZOOM),
    ("com.hnc.Discord", CallApp.DISCORD),
    ("com.tinyspeck.slackmacgap", CallApp.SLACK),
    ("com.tinyspeck.slack", CallApp.SLACK),
)


class BundleIdCallContext:
    def __init__(self, detector: CoreAudioMicDetector) -> None:
        self._detector = detector

    def identify(self) -> CallApp:
        for bundle in self._detector.last_trigger_bundles:
            for prefix, app in _BUNDLE_PREFIX_TO_APP:
                if bundle.startswith(prefix):
                    return app
        return CallApp.UNKNOWN
