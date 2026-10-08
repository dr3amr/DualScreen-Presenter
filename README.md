# DualScreen Presenter — Broadcast Console

DualScreen Presenter is a Windows desktop application for presenting photos and videos on a second monitor, TV, or projector while controlling playback from an operator window.

The application is written in Python and uses **PyQt6** for its interface, screen management, image rendering, and Qt Multimedia video and audio playback. It is provided under the **GNU General Public License, version 3 (GPLv3)**.

## Features

- Fullscreen projection to a selected display, with a black background and preserved media aspect ratio.
- Operator preview with floating ON/OFF AIR and slideshow status bubbles.
- Manual next/back navigation and a random navigation option.
- Timed slideshows with intervals from 2 to 60 seconds, optional automatic start with projection, and an option to let videos finish.
- Folder loading, optional subfolder scanning, search, sorting, and photo/video filters.
- Distinct photo and filmstrip icons in the file list.
- Video play/pause, seeking, looping, volume, and mute/unmute controls.
- Five themes: Obsidian Neon, Midnight Studio, Cyberpunk Amber, Slate Graphite, and Dark Gray. Dark Gray uses neutral backgrounds throughout the interface.
- Saved window, display, theme, folder, slideshow, and audio preferences.

## Run the Windows executable

Double-click `DualScreenPresenter.exe`. No Python installation is needed, and the application opens without a console window.

The executable bundles Python, PyQt6, the required Qt libraries and multimedia plugins, `app_icon.ico`, and the sample media. PyInstaller extracts bundled dependencies to a temporary directory at startup.

The executable is a single file for running the application. Redistributing it must also comply with the license and source-code requirements described below.

## Run from source

Development and builds have been tested with **64-bit Windows and Python 3.14.5**. The application runtime dependency is **PyQt6**, as listed in `requirements.txt`.

From the project directory, run these commands in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Pillow, OpenCV, and NumPy are not required by the application.

## Basic usage

1. Click **Choose Folder...** and select a folder containing photos or videos.
2. Select a file from the list, or use **Next**, **Back**, and **Random**.
3. Choose the audience display from the **Display** selector.
4. Click **Start Projecting** to open the fullscreen audience window.
5. For automatic playback, choose an interval and click **Start Slideshow**. Enable **Let videos finish** if each video should complete before advancing.
6. Use **Stop Projecting** to close the audience window. Video controls and the playback timer appear beneath the operator preview when a video is selected.

## Build the executable

Install the build and executable-verification tools in the same environment:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller pefile
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm DualScreenPresenter.spec
```

The output is `dist/DualScreenPresenter.exe`. The spec produces a single Windows GUI executable, includes the application icon and sample media, and resolves its inputs relative to the spec file. When building from another directory, pass the full path to `DualScreenPresenter.spec`.

## Verification

```powershell
.\.venv\Scripts\python.exe tests/test_preview_widget.py -v
.\.venv\Scripts\python.exe tests/verify_executable.py
```

The preview checks run Qt offscreen with isolated settings. They cover image resizing, video-frame rendering, playback of a sample video, status updates, Dark Gray theme styling, mute-button sizing, and the single playback timer.

Run the executable check after building. It verifies the Windows GUI subsystem, embedded icon, sample media, application modules, Qt libraries, and FFmpeg video backend.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| Right Arrow, Space, Page Down | Next media item |
| Left Arrow, Page Up | Previous media item |
| R | Toggle random navigation |
| F5 | Start projecting |
| Escape | Stop projecting |
| B or period (`.`) | Toggle a blank audience screen |
| P | Start or pause the slideshow |
| M | Toggle mute/unmute |
| Up Arrow / Down Arrow | Increase/decrease volume |

Video play/pause is controlled by the **Play/Pause** button. Navigation and projection shortcuts also work while the audience window has focus.

## Recognized media formats

- **Photos:** JPG, JPEG, PNG, BMP, GIF, WebP, TIFF, and TIF.
- **Videos:** MP4, M4V, MKV, AVI, MOV, WMV, WebM, and FLV.

Video playback depends on the codecs supported by the bundled Qt Multimedia backend.

## License and PyQt6

**DualScreen Presenter — Broadcast Console is provided under the GNU General Public License, version 3 (GPLv3).** You may use, modify, and redistribute the application under the terms of that license. The application is provided without warranty, to the extent permitted by applicable law.

When redistributing the application or modified versions, retain the applicable license and copyright notices and provide the corresponding source code as required by GPLv3, including the materials needed to build the distributed version.

Read the [full GPLv3 license text](LICENSE).

This project uses the GPL-licensed version of **PyQt6**. Riverbank Computing makes PyQt6 available under GPLv3 or a separate commercial license; PyQt6 is not LGPL-licensed. See [Riverbank's PyQt licensing information](https://www.riverbankcomputing.com/software/pyqt/intro) and [licensing FAQ](https://www.riverbankcomputing.com/commercial/license-faq).

Third-party components bundled with the executable, including Python, Qt, and FFmpeg, retain their respective licenses and notices. The application's GPLv3 declaration does not replace those licenses.
