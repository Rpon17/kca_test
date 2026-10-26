"""Bridge SentinelCV RTSP open/EOF signals to the asyncio controller."""
import asyncio
import functools
import time

class RtspBoundaryHooks:

    def __init__(self, pipeline_cls, reader_cls, loop, stream_events):
        self.pipeline_cls = pipeline_cls
        self.reader_cls = reader_cls
        self.loop = loop
        self.stream_events = stream_events
        self.original_open_capture = pipeline_cls._open_capture
        self.original_latest = reader_cls.latest
        self.original_reader_run = reader_cls._run

    def install(self):
        CameraDetectionPipeline = self.pipeline_cls
        _RtspReader = self.reader_cls
        loop = self.loop
        stream_events = self.stream_events
        original_open_capture = CameraDetectionPipeline._open_capture
        original_latest = _RtspReader.latest
        original_reader_run = _RtspReader._run

        @functools.wraps(original_open_capture)
        def capture_with_boundary(self, *args, **kwargs):
            cap = original_open_capture(self, *args, **kwargs)
            if cap is not None and getattr(self, 'is_rtsp_source', False):
                loop.call_soon_threadsafe(stream_events.put_nowait, ('open', time.monotonic()))
            return cap

        def latest_without_stale_frame(self):
            if not self._t.is_alive():
                return None
            return original_latest(self)

        def reader_with_eof_signal(self):
            original_reader_run(self)
            if self._running:
                loop.call_soon_threadsafe(stream_events.put_nowait, ('eof', time.monotonic()))
        CameraDetectionPipeline._open_capture = capture_with_boundary
        _RtspReader.latest = latest_without_stale_frame
        _RtspReader._run = reader_with_eof_signal

    def restore(self):
        self.pipeline_cls._open_capture = self.original_open_capture
        self.reader_cls.latest = self.original_latest
        self.reader_cls._run = self.original_reader_run
