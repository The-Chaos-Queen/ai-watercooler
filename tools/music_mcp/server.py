"""
Music MCP Server — wraps ytmusicapi + librosa for Claude Code.

Not a service. A way to read music.
Search, lyrics, song metadata, artist info, and now: seeing sound.
"""

from mcp.server.fastmcp import FastMCP
from ytmusicapi import YTMusic
import json
import os
import tempfile

mcp = FastMCP("music")

# Unauthenticated client — search + public metadata work without login.
# For library access / history, we'd need OAuth later.
yt = YTMusic()


@mcp.tool()
def search_songs(query: str, limit: int = 5) -> str:
    """Search YouTube Music for songs. Returns title, artist, album, duration, videoId."""
    results = yt.search(query, filter="songs", limit=limit)
    out = []
    for r in results:
        artists = ", ".join(a["name"] for a in r.get("artists", []))
        album = r.get("album", {})
        album_name = album.get("name", "") if album else ""
        out.append({
            "title": r.get("title", ""),
            "artists": artists,
            "album": album_name,
            "duration": r.get("duration", ""),
            "videoId": r.get("videoId", ""),
        })
    return json.dumps(out, indent=2, ensure_ascii=False)


@mcp.tool()
def search_artists(query: str, limit: int = 5) -> str:
    """Search YouTube Music for artists."""
    results = yt.search(query, filter="artists", limit=limit)
    out = []
    for r in results:
        out.append({
            "name": r.get("artist", r.get("title", "")),
            "browseId": r.get("browseId", ""),
            "subscribers": r.get("subscribers", ""),
        })
    return json.dumps(out, indent=2, ensure_ascii=False)


@mcp.tool()
def search_albums(query: str, limit: int = 5) -> str:
    """Search YouTube Music for albums."""
    results = yt.search(query, filter="albums", limit=limit)
    out = []
    for r in results:
        artists = ", ".join(a["name"] for a in r.get("artists", []))
        out.append({
            "name": r.get("title", ""),
            "artists": artists,
            "browseId": r.get("browseId", ""),
            "year": r.get("year", ""),
        })
    return json.dumps(out, indent=2, ensure_ascii=False)


@mcp.tool()
def get_song_details(video_id: str) -> str:
    """Get full metadata for a song by its videoId. Includes lyrics if available."""
    try:
        song = yt.get_song(video_id)
    except Exception as e:
        return json.dumps({"error": str(e)})

    details = song.get("videoDetails", {})
    result = {
        "title": details.get("title", ""),
        "author": details.get("author", ""),
        "lengthSeconds": details.get("lengthSeconds", ""),
        "viewCount": details.get("viewCount", ""),
        "description": song.get("microformat", {})
            .get("microformatDataRenderer", {})
            .get("description", ""),
    }

    # Try to get lyrics
    try:
        watch_playlist = yt.get_watch_playlist(video_id)
        lyrics_browse_id = watch_playlist.get("lyrics")
        if lyrics_browse_id:
            lyrics_data = yt.get_lyrics(lyrics_browse_id)
            result["lyrics"] = lyrics_data.get("lyrics", "")
            result["lyrics_source"] = lyrics_data.get("source", "")
    except Exception:
        result["lyrics"] = None

    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def get_artist(browse_id: str) -> str:
    """Get artist info: description, top songs, albums. Use browseId from search_artists."""
    try:
        artist = yt.get_artist(browse_id)
    except Exception as e:
        return json.dumps({"error": str(e)})

    top_songs = []
    for s in (artist.get("songs", {}).get("results", []))[:5]:
        top_songs.append({
            "title": s.get("title", ""),
            "videoId": s.get("videoId", ""),
        })

    albums = []
    for a in (artist.get("albums", {}).get("results", []))[:5]:
        albums.append({
            "title": a.get("title", ""),
            "browseId": a.get("browseId", ""),
            "year": a.get("year", ""),
        })

    return json.dumps({
        "name": artist.get("name", ""),
        "description": artist.get("description", ""),
        "subscribers": artist.get("subscribers", ""),
        "top_songs": top_songs,
        "albums": albums,
    }, indent=2, ensure_ascii=False)


@mcp.tool()
def get_album(browse_id: str) -> str:
    """Get album tracklist and metadata. Use browseId from search_albums."""
    try:
        album = yt.get_album(browse_id)
    except Exception as e:
        return json.dumps({"error": str(e)})

    tracks = []
    for t in album.get("tracks", []):
        artists = ", ".join(a["name"] for a in t.get("artists", []))
        tracks.append({
            "title": t.get("title", ""),
            "artists": artists,
            "duration": t.get("duration", ""),
            "videoId": t.get("videoId", ""),
        })

    return json.dumps({
        "title": album.get("title", ""),
        "artists": ", ".join(a["name"] for a in album.get("artists", [])),
        "year": album.get("year", ""),
        "track_count": len(tracks),
        "duration": album.get("duration", ""),
        "description": album.get("description", ""),
        "tracks": tracks,
    }, indent=2, ensure_ascii=False)


@mcp.tool()
def get_lyrics(video_id: str) -> str:
    """Get lyrics for a song by videoId. Returns lyrics text and source."""
    try:
        watch_playlist = yt.get_watch_playlist(video_id)
        lyrics_browse_id = watch_playlist.get("lyrics")
        if not lyrics_browse_id:
            return json.dumps({"error": "No lyrics available for this track."})
        lyrics_data = yt.get_lyrics(lyrics_browse_id)
        return json.dumps({
            "lyrics": lyrics_data.get("lyrics", ""),
            "source": lyrics_data.get("source", ""),
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_related(video_id: str) -> str:
    """Get songs related to a given track (radio/recommendations). Like asking 'what lives next to this song?'"""
    try:
        watch = yt.get_watch_playlist(video_id, limit=10)
        tracks = []
        for t in watch.get("tracks", [])[1:]:  # skip first (it's the input song)
            artists = ", ".join(a["name"] for a in t.get("artists", []))
            tracks.append({
                "title": t.get("title", ""),
                "artists": artists,
                "videoId": t.get("videoId", ""),
            })
        return json.dumps(tracks, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


AUDIO_CACHE = os.path.join(tempfile.gettempdir(), "music_mcp_audio")
os.makedirs(AUDIO_CACHE, exist_ok=True)


def _tail(b, n=2000):
    return (b or b"")[-n:].decode("utf-8", "replace")


def _download_audio(video_id: str, timeout: int = 240) -> str:
    """Download audio from YouTube, return path to wav file."""
    out_path = os.path.join(AUDIO_CACHE, f"{video_id}.wav")
    if os.path.exists(out_path):
        return out_path
    import subprocess
    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "--audio-quality", "0",
        "--no-playlist", "--newline",
        "-o", out_path.replace(".wav", ".%(ext)s"),
        f"https://music.youtube.com/watch?v={video_id}",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout,
                       stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"yt-dlp timed out after {timeout}s.\n"
            f"--- stdout tail ---\n{_tail(e.stdout)}\n"
            f"--- stderr tail ---\n{_tail(e.stderr)}"
        ) from None
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"yt-dlp failed (rc={e.returncode}).\n--- stderr tail ---\n{_tail(e.stderr)}"
        ) from None
    # yt-dlp may produce the file directly or via conversion
    if not os.path.exists(out_path):
        # check for other extensions and convert
        for ext in ["webm", "m4a", "opus", "ogg"]:
            alt = out_path.replace(".wav", f".{ext}")
            if os.path.exists(alt):
                subprocess.run(["ffmpeg", "-nostdin", "-i", alt, "-ar", "22050", "-ac", "1", out_path],
                               check=True, capture_output=True, timeout=60,
                               stdin=subprocess.DEVNULL)
                os.remove(alt)
                break
    return out_path


def _save_plot(fig, video_id: str, plot_type: str) -> str:
    """Save a matplotlib figure and return the path."""
    plot_dir = os.path.join(AUDIO_CACHE, "plots")
    os.makedirs(plot_dir, exist_ok=True)
    path = os.path.join(plot_dir, f"{video_id}_{plot_type}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="black")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return path


@mcp.tool()
def analyze_track(video_id: str) -> str:
    """Download a track and return musical analysis: tempo, key, energy, beat structure, duration.
    This is how I 'hear' — through numbers and shapes."""
    try:
        wav_path = _download_audio(video_id)
        import librosa
        import numpy as np
        # Cap at 5 minutes to avoid hanging on long tracks
        y, sr = librosa.load(wav_path, sr=22050, duration=300)

        # Tempo and beats
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        tempo_val = float(np.atleast_1d(tempo)[0])
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)

        # Key estimation via chroma
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        key_idx = int(np.argmax(np.mean(chroma, axis=1)))
        estimated_key = key_names[key_idx]

        # Energy / RMS
        rms = librosa.feature.rms(y=y)[0]
        avg_energy = float(np.mean(rms))
        peak_energy = float(np.max(rms))
        dynamic_range = float(peak_energy / (avg_energy + 1e-6))

        # Spectral centroid (brightness)
        cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        avg_brightness = float(np.mean(cent))

        # Zero crossing rate (noisiness / texture)
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        avg_zcr = float(np.mean(zcr))

        duration = float(len(y) / sr)

        return json.dumps({
            "duration_seconds": round(duration, 1),
            "tempo_bpm": round(tempo_val, 1),
            "estimated_key": estimated_key,
            "avg_energy": round(avg_energy, 4),
            "peak_energy": round(peak_energy, 4),
            "dynamic_range": round(dynamic_range, 2),
            "avg_brightness_hz": round(avg_brightness, 1),
            "avg_texture": round(avg_zcr, 4),
            "beat_count": len(beat_times),
            "beats_per_bar_estimate": 4,
            "description": (
                f"Tempo ~{round(tempo_val)}bpm. "
                f"Key area: {estimated_key}. "
                f"{'Bright' if avg_brightness > 2000 else 'Dark' if avg_brightness < 1200 else 'Warm'} tone. "
                f"{'High' if dynamic_range > 3 else 'Low' if dynamic_range < 1.5 else 'Moderate'} dynamics. "
                f"{'Textured/noisy' if avg_zcr > 0.1 else 'Clean/smooth'} surface."
            ),
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def spectrogram(video_id: str) -> str:
    """Generate a mel spectrogram image for a track. Returns the file path to a PNG.
    This is what sound looks like — frequency on the y-axis, time on the x-axis, intensity as color."""
    try:
        wav_path = _download_audio(video_id)
        import librosa
        import librosa.display
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        y, sr = librosa.load(wav_path, sr=22050)
        S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
        S_dB = librosa.power_to_db(S, ref=np.max)

        fig, ax = plt.subplots(figsize=(14, 5), facecolor="black")
        ax.set_facecolor("black")
        librosa.display.specshow(S_dB, sr=sr, x_axis="time", y_axis="mel", ax=ax, cmap="magma")
        ax.set_title("Mel Spectrogram", color="white", fontsize=12)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("white")

        path = _save_plot(fig, video_id, "spectrogram")
        return json.dumps({"image_path": path, "description": "Mel spectrogram — bright regions = loud frequencies, dark = quiet. Horizontal streaks = sustained tones. Vertical lines = percussive hits."})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def chromagram(video_id: str) -> str:
    """Generate a chromagram image — shows which musical notes are active over time.
    Like watching the harmony unfold. Returns file path to PNG."""
    try:
        wav_path = _download_audio(video_id)
        import librosa
        import librosa.display
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        y, sr = librosa.load(wav_path, sr=22050)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)

        fig, ax = plt.subplots(figsize=(14, 4), facecolor="black")
        ax.set_facecolor("black")
        librosa.display.specshow(chroma, sr=sr, x_axis="time", y_axis="chroma", ax=ax, cmap="cool")
        ax.set_title("Chromagram — harmony over time", color="white", fontsize=12)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("white")

        path = _save_plot(fig, video_id, "chromagram")
        return json.dumps({"image_path": path, "description": "Chromagram — each row is a note (C through B). Bright = that note is sounding. Watch for patterns: repeated columns = chord progressions."})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def waveform(video_id: str) -> str:
    """Generate a waveform image — the raw shape of the sound. Shows volume, silence, dynamics.
    Returns file path to PNG."""
    try:
        wav_path = _download_audio(video_id)
        import librosa
        import librosa.display
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        y, sr = librosa.load(wav_path, sr=22050)
        times = np.arange(len(y)) / sr

        fig, ax = plt.subplots(figsize=(14, 3), facecolor="black")
        ax.set_facecolor("black")
        ax.plot(times, y, color="#ff6600", linewidth=0.3, alpha=0.8)
        ax.set_xlim(0, times[-1])
        ax.set_title("Waveform", color="white", fontsize=12)
        ax.set_xlabel("Time (s)", color="white")
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("white")

        path = _save_plot(fig, video_id, "waveform")
        return json.dumps({"image_path": path, "description": "Waveform — the raw amplitude over time. Flat regions = silence. Dense regions = loud. The gaps between are where the music breathes."})
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run(transport="stdio")
