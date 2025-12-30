#!/usr/bin/env python3
"""
YouTube to Summary Pipeline (v2)
=================================

Downloads a YouTube video transcript and prepares for summary generation.
Uses YouTube Transcript API as primary method (instant), falls back to Whisper if needed.

Usage:
    python yt_to_summary.py <youtube_url>
    python yt_to_summary.py <youtube_url> --use-whisper  # Force Whisper transcription

Output:
    Creates folder: {Channel}/{Video Title}/
    Creates file: transcript.txt (with source URL header)
    
After transcript extraction, the LLM agent should use PROMPT.md to generate summary.md.
"""

import subprocess
import sys
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


def clean_name(name: str, max_length: int = 80) -> str:
    """Clean a string for use as a folder name."""
    if not name:
        return "unknown"
    
    # Remove or replace invalid characters
    cleaned = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace problematic characters with underscores
    cleaned = re.sub(r'[\[\]\(\)\{\}\+\=\&\^\%\$\#\@\!\,\.\;\'\"]', '_', cleaned)
    # Remove multiple consecutive underscores/spaces
    cleaned = re.sub(r'[_\s]+', ' ', cleaned)
    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()
    # Limit length
    cleaned = cleaned[:max_length]
    
    return cleaned if cleaned else "unknown"


def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from YouTube URL."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'  # Just the ID
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_video_metadata(url: str) -> tuple[str, str]:
    """Extract channel name and video title from YouTube URL."""
    print(f"Fetching metadata for: {url}")
    
    result = subprocess.run(
        ["yt-dlp", "--print", "%(channel)s", "--print", "%(title)s", url],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode != 0:
        print(f"Error fetching metadata: {result.stderr}")
        sys.exit(1)
    
    lines = result.stdout.strip().split("\n")
    if len(lines) < 2:
        print(f"Unexpected metadata format: {result.stdout}")
        sys.exit(1)
    
    channel = clean_name(lines[0])
    title = clean_name(lines[1])
    
    print(f"Channel: {channel}")
    print(f"Title: {title}")
    
    return channel, title


def get_youtube_transcript(video_id: str) -> Optional[str]:
    """Try to get transcript using YouTube Transcript API (fast, free)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        print("Attempting to fetch YouTube captions...")
        
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id=video_id)
        
        print(f"Found {'auto-generated' if transcript.is_generated else 'manual'} transcript in {transcript.language}")
        
        # Convert to plain text
        text_parts = [snippet.text for snippet in transcript]
        full_text = " ".join(text_parts)
        
        # Clean up and add paragraph breaks
        full_text = re.sub(r'\s+', ' ', full_text)
        full_text = re.sub(r'([.!?])\s+', r'\1\n\n', full_text)
        
        print(f"Successfully extracted transcript ({len(full_text)} characters)")
        return full_text
        
    except ImportError:
        print("youtube-transcript-api not installed. Install with: pip install youtube-transcript-api")
        return None
    except Exception as e:
        print(f"Could not fetch YouTube transcript: {e}")
        return None


def run_whisper_transcription(url: str, output_dir: Path) -> Optional[Path]:
    """Run Whisper transcription using yt-stt (slower but works on any video)."""
    script_dir = Path(__file__).parent.parent.parent / "yt-stt"
    yt_stt_script = script_dir / "youtube_stt_screenshots.py"
    
    if not yt_stt_script.exists():
        print(f"Error: yt-stt script not found at {yt_stt_script}")
        return None
    
    cmd = [
        sys.executable,
        str(yt_stt_script),
        url,
        "--transcript-only",
        "--keep-video",
        "--output", str(output_dir)
    ]
    
    print("\nRunning Whisper transcription (this may take several minutes)...")
    print("-" * 50)
    
    result = subprocess.run(cmd, cwd=str(script_dir))
    
    print("-" * 50)
    
    # Find the transcript file
    transcript_files = list(output_dir.rglob("transcript_clean.txt"))
    if transcript_files:
        return transcript_files[0]
    return None


def save_transcript(output_dir: Path, url: str, transcript_text: str, method: str) -> Path:
    """Save transcript to file with metadata header."""
    transcript_path = output_dir / "transcript.txt"
    
    with open(transcript_path, 'w', encoding='utf-8') as f:
        f.write(f"Source: {url}\n")
        f.write(f"Transcribed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Method: {method}\n")
        f.write("=" * 50 + "\n\n")
        f.write(transcript_text)
    
    print(f"Saved transcript to: {transcript_path}")
    return transcript_path


def cleanup_media_files(output_dir: Path):
    """Remove any leftover audio/video files and empty directories."""
    media_extensions = {'.mp4', '.mp3', '.wav', '.webm', '.m4a', '.avi', '.mov', '.mkv'}
    
    for file in output_dir.rglob("*"):
        if file.is_file() and file.suffix.lower() in media_extensions:
            print(f"Cleaning up: {file.name}")
            file.unlink()
    
    # Remove empty subdirectories (bottom-up)
    for subdir in sorted(output_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if subdir.is_dir():
            try:
                if not any(subdir.iterdir()):
                    subdir.rmdir()
            except OSError:
                pass


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube to Summary Pipeline")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--use-whisper", "-w", action="store_true",
                        help="Force Whisper transcription (skip YouTube API)")
    parser.add_argument("--output-base", "-o", default=None,
                        help="Base output directory (default: Trust Safety Alignment folder)")
    
    args = parser.parse_args()
    
    # Determine base output directory
    if args.output_base:
        base_dir = Path(args.output_base)
    else:
        base_dir = Path(__file__).parent.parent  # Trust Safety Alignment folder
    
    print("=" * 60)
    print("YouTube to Summary Pipeline v2")
    print("=" * 60)
    
    # Step 1: Get metadata
    channel, title = get_video_metadata(args.url)
    video_id = extract_video_id(args.url)
    
    # Step 2: Create output directory
    # User requested format: <Author or Org>-<Title of the video>
    # e.g. "Neel Nanda-Our Pivot To Pragmatic Interpretability"
    folder_name = f"{channel}-{title}"
    output_dir = base_dir / folder_name
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput folder: {output_dir}")
    
    # Step 3: Get transcript (try YouTube API first, fall back to Whisper)
    transcript_text = None
    method = None
    
    if not args.use_whisper and video_id:
        transcript_text = get_youtube_transcript(video_id)
        if transcript_text:
            method = "YouTube Transcript API"
    
    if transcript_text is None:
        print("\nFalling back to Whisper transcription...")
        whisper_transcript = run_whisper_transcription(args.url, output_dir)
        
        if whisper_transcript and whisper_transcript.exists():
            with open(whisper_transcript, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
            method = "OpenAI Whisper Large"
            
            # Move files from nested folder to output_dir
            nested_folder = whisper_transcript.parent
            if nested_folder != output_dir:
                for file in nested_folder.iterdir():
                    if file.is_file() and file.name != "transcript.txt":
                        target = output_dir / file.name
                        if not target.exists():
                            shutil.move(str(file), str(target))
    
    if transcript_text is None:
        print("\n❌ Failed to extract transcript!")
        sys.exit(1)
    
    # Step 4: Save transcript with metadata
    transcript_path = save_transcript(output_dir, args.url, transcript_text, method)
    
    # Step 5: Cleanup media files
    cleanup_media_files(output_dir)
    
    print("\n" + "=" * 60)
    print("✅ Pipeline completed successfully!")
    print("=" * 60)
    print(f"\n📁 Output folder: {output_dir}")
    print(f"📄 Transcript: {transcript_path}")
    print(f"🔧 Method used: {method}")
    print(f"\n" + "=" * 60)
    print("📝 NEXT STEP FOR LLM AGENT:")
    print("=" * 60)
    print(f"1. Read transcript from: {transcript_path}")
    print(f"2. Read PROMPT.md from: {base_dir / 'PROMPT.md'}")
    print(f"3. Generate summary following PROMPT.md template")
    print(f"4. Save as: {output_dir / 'summary.md'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
