import time
from threading import Lock
from config import EVENT_NAME_MAP
from xml_writer import seconds_to_time, write_sa_xml

class EventCollector:

    def __init__(self, filenames: list[str]):
        self.filenames = filenames
        self.index = 0
        self.video_started = time.monotonic()
        self.events = []
        self.seen = set()
        self.lock = Lock()

    @property
    def current_filename(self):
        if self.index >= len(self.filenames):
            return None
        return self.filenames[self.index]

    async def on_event(self, event, response_ms=None):
        with self.lock:
            filename = self.current_filename
            if filename is None:
                return
            event_type = getattr(event, 'event_type', '')
            event_type = getattr(event_type, 'value', event_type)
            event_type = str(event_type).upper()
            description = EVENT_NAME_MAP.get(event_type)
            if description is None:
                print(f'[주의] {filename}: {event_type} 매핑 없음')
                return
            elapsed = int(time.monotonic() - self.video_started)
            start_time = seconds_to_time(elapsed)
            track_id = getattr(event, 'track_id', None)
            dedupe_key = (event_type, track_id, start_time)
            if dedupe_key in self.seen:
                return
            self.seen.add(dedupe_key)
            self.events.append({'StartTime': start_time, 'AlarmDescription': description, 'AlarmDuration': '00:01:00'})
            print(f'[이벤트] {filename} {start_time} {description}')

    def finish_current_video(self):
        with self.lock:
            filename = self.current_filename
            if filename is None:
                return None
            output_path = write_sa_xml(filename, list(self.events))
            print(f'[XML 저장] {output_path}')
            print(f'[이벤트 수] {len(self.events)}')
            self.index += 1
            self.events.clear()
            self.seen.clear()
            self.video_started = time.monotonic()
            return output_path
