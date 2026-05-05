from collections.abc import Sequence

from transcribe_meeting_audio.domain.diarization import SpeakerSegment
from transcribe_meeting_audio.domain.meeting import (
    AttributedSegment,
    Meeting,
    MeetingTranscript,
)
from transcribe_meeting_audio.domain.transcript import TranscriptSegment
from transcribe_meeting_audio.ports.transcriber import Transcriber


class TranscribeMeeting:
    """Transcribes both tracks of a meeting and merges them into a single
    speaker-attributed, time-ordered transcript.

    Mic segments are tagged with `self_speaker`. Loopback segments are tagged
    by overlap with the supplied `speaker_turns` (output of a diarizer). When
    no speaker turns are supplied, loopback segments fall back to
    `other_speaker`.
    """

    def __init__(
        self,
        transcriber: Transcriber,
        self_speaker: str = "you",
        other_speaker: str = "other",
    ) -> None:
        self._transcriber = transcriber
        self._self = self_speaker
        self._other = other_speaker

    def transcribe(
        self,
        meeting: Meeting,
        speaker_turns: Sequence[SpeakerSegment] = (),
    ) -> MeetingTranscript:
        mic_transcript = self._transcriber.transcribe(meeting.mic_track)
        loopback_transcript = self._transcriber.transcribe(meeting.loopback_track)

        segments: list[AttributedSegment] = []
        for s in mic_transcript.segments:
            segments.append(
                AttributedSegment(start=s.start, end=s.end, speaker=self._self, text=s.text)
            )
        for s in loopback_transcript.segments:
            speaker = self._attribute(s, speaker_turns)
            segments.append(
                AttributedSegment(start=s.start, end=s.end, speaker=speaker, text=s.text)
            )
        segments.sort(key=lambda s: s.start)

        duration = max(
            meeting.mic_track.end_at - meeting.mic_track.start_at,
            meeting.loopback_track.end_at - meeting.loopback_track.start_at,
        )
        return MeetingTranscript(
            label=meeting.label, duration=duration, segments=tuple(segments)
        )

    def _attribute(
        self, segment: TranscriptSegment, turns: Sequence[SpeakerSegment]
    ) -> str:
        if not turns:
            return self._other
        best_speaker = self._other
        best_overlap = 0.0
        for turn in turns:
            overlap = max(0.0, min(segment.end, turn.end) - max(segment.start, turn.start))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = turn.speaker_id
        return best_speaker
