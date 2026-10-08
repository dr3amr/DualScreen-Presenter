"""
media_manager.py - Media file discovery, playlist management, and navigation.
Supports images and videos with robust filtering, sorting, and history tracking.
"""

import os
import random
from typing import List, Optional


SUPPORTED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.tif'}
SUPPORTED_VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm', '.m4v', '.flv'}


def format_file_size(size_bytes: int) -> str:
    """Format bytes into a readable string (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class MediaItem:
    """Represents an image or video file."""
    def __init__(self, file_path: str):
        self.path = os.path.abspath(file_path)
        self.filename = os.path.basename(file_path)
        self.ext = os.path.splitext(self.filename)[1].lower()
        self.is_video = self.ext in SUPPORTED_VIDEO_EXTS
        self.is_image = self.ext in SUPPORTED_IMAGE_EXTS
        self.media_type = 'video' if self.is_video else 'image'

        try:
            stat = os.stat(self.path)
            self.size_bytes = stat.st_size
            self.mtime = stat.st_mtime
        except Exception:
            self.size_bytes = 0
            self.mtime = 0

        self.size_str = format_file_size(self.size_bytes)
        self.width = 0
        self.height = 0
        self.duration_ms = 0

    def __repr__(self):
        return f"<MediaItem {self.filename} ({self.media_type})>"


class MediaManager:
    """Manages folder scanning, media collections, filtering, sorting, and navigation."""

    def __init__(self):
        self.current_folder: Optional[str] = None
        self.all_items: List[MediaItem] = []
        self.filtered_items: List[MediaItem] = []
        self.current_index: int = -1

        # Random shuffle pool for non-repeating random navigation
        self._shuffle_pool: List[int] = []
        self._history: List[int] = []
        self._history_pointer: int = -1

        # Filter and sort states
        self.search_query: str = ""
        self.media_filter: str = "all"  # 'all', 'image', 'video'
        self.sort_key: str = "name"    # 'name', 'date', 'size', 'type'
        self.sort_ascending: bool = True

    def load_folder(self, folder_path: str, recursive: bool = False) -> int:
        """Scan a folder for supported media files."""
        if not os.path.isdir(folder_path):
            return 0

        self.current_folder = os.path.abspath(folder_path)
        items: List[MediaItem] = []

        if recursive:
            for root, _, files in os.walk(self.current_folder):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_IMAGE_EXTS or ext in SUPPORTED_VIDEO_EXTS:
                        full_path = os.path.join(root, f)
                        items.append(MediaItem(full_path))
        else:
            try:
                for entry in os.scandir(self.current_folder):
                    if entry.is_file():
                        ext = os.path.splitext(entry.name)[1].lower()
                        if ext in SUPPORTED_IMAGE_EXTS or ext in SUPPORTED_VIDEO_EXTS:
                            items.append(MediaItem(entry.path))
            except Exception as e:
                print(f"Error scanning folder: {e}")

        self.all_items = items
        self._reset_navigation()
        self.apply_filter_and_sort()
        return len(self.filtered_items)

    def _reset_navigation(self):
        self.current_index = -1
        self._history.clear()
        self._history_pointer = -1
        self._rebuild_shuffle_pool()

    def _rebuild_shuffle_pool(self):
        n = len(self.filtered_items)
        self._shuffle_pool = list(range(n))
        random.shuffle(self._shuffle_pool)

    def apply_filter_and_sort(self):
        """Filters and sorts media items."""
        query = self.search_query.strip().lower()
        filtered = []

        for item in self.all_items:
            # Type filter
            if self.media_filter == 'image' and not item.is_image:
                continue
            if self.media_filter == 'video' and not item.is_video:
                continue

            # Text search filter
            if query and query not in item.filename.lower():
                continue

            filtered.append(item)

        # Sort items
        if self.sort_key == "name":
            filtered.sort(key=lambda x: x.filename.lower(), reverse=not self.sort_ascending)
        elif self.sort_key == "date":
            filtered.sort(key=lambda x: x.mtime, reverse=not self.sort_ascending)
        elif self.sort_key == "size":
            filtered.sort(key=lambda x: x.size_bytes, reverse=not self.sort_ascending)
        elif self.sort_key == "type":
            filtered.sort(key=lambda x: (x.media_type, x.filename.lower()), reverse=not self.sort_ascending)

        self.filtered_items = filtered
        self._rebuild_shuffle_pool()

        # Update current index
        if self.filtered_items:
            if self.current_index < 0 or self.current_index >= len(self.filtered_items):
                self.current_index = 0
        else:
            self.current_index = -1

    def count(self) -> int:
        return len(self.filtered_items)

    def image_count(self) -> int:
        return sum(1 for item in self.filtered_items if item.is_image)

    def video_count(self) -> int:
        return sum(1 for item in self.filtered_items if item.is_video)

    def get_current_item(self) -> Optional[MediaItem]:
        if 0 <= self.current_index < len(self.filtered_items):
            return self.filtered_items[self.current_index]
        return None

    def jump_to_index(self, index: int) -> Optional[MediaItem]:
        if 0 <= index < len(self.filtered_items):
            self.current_index = index
            self._record_history(index)
            return self.filtered_items[self.current_index]
        return None

    def next_item(self) -> Optional[MediaItem]:
        """Manually advance to the next item (wraps around)."""
        if not self.filtered_items:
            return None
        self.current_index = (self.current_index + 1) % len(self.filtered_items)
        self._record_history(self.current_index)
        return self.filtered_items[self.current_index]

    def prev_item(self) -> Optional[MediaItem]:
        """Manually advance to the previous item (or previous in history)."""
        if not self.filtered_items:
            return None

        # If we have prior history from random / jumps, step backwards in history
        if self._history_pointer > 0:
            self._history_pointer -= 1
            hist_idx = self._history[self._history_pointer]
            if 0 <= hist_idx < len(self.filtered_items):
                self.current_index = hist_idx
                return self.filtered_items[self.current_index]

        # Otherwise standard sequential previous
        self.current_index = (self.current_index - 1 + len(self.filtered_items)) % len(self.filtered_items)
        return self.filtered_items[self.current_index]

    def random_item(self) -> Optional[MediaItem]:
        """Picks a random item without immediate repetition."""
        if not self.filtered_items:
            return None
        if len(self.filtered_items) == 1:
            return self.filtered_items[0]

        # Refill pool if depleted
        if not self._shuffle_pool:
            self._rebuild_shuffle_pool()

        # Pop next random index, avoiding same item consecutively if possible
        next_idx = self._shuffle_pool.pop()
        if next_idx == self.current_index and self._shuffle_pool:
            next_idx, self._shuffle_pool[0] = self._shuffle_pool[0], next_idx

        self.current_index = next_idx
        self._record_history(self.current_index)
        return self.filtered_items[self.current_index]

    def _record_history(self, index: int):
        # Truncate any forward history if we branched
        if self._history_pointer < len(self._history) - 1:
            self._history = self._history[:self._history_pointer + 1]
        self._history.append(index)
        # Cap history to 200 entries
        if len(self._history) > 200:
            self._history.pop(0)
        self._history_pointer = len(self._history) - 1
