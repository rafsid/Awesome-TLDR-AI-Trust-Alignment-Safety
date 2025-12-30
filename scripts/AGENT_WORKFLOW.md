# Agent Workflow: YouTube URL → Transcript → Summary

This document provides step-by-step instructions for LLM agents to process a YouTube URL into a cognitive-science-optimized summary.

---

## Prerequisites

You need access to these tools:
- `run_command` (for running Python scripts and shell commands)
- File read/write tools
- Web search capability (for verifying Further Reading URLs)

---

## Workflow Steps

### Step 1: Extract Video Metadata

Run yt-dlp to get the video title and channel name:

```bash
yt-dlp --print "%(channel)s" --print "%(title)s" "<YOUTUBE_URL>"
```

**Output**: Two lines - channel name, then video title.

### Step 2: Create Folder Structure

Create a folder in the Trust Safety Alignment project:
```
/Users/rafatsiddiqui/Downloads/Projects/Trust Safety Alignment/{Channel}/{Video Title}/
```

Clean the folder names by:
- Removing special characters: `<>:"/\|?*`
- Replacing spaces with underscores or keeping them
- Limiting to 80 characters

### Step 3: Run Transcription

Execute the transcription script:

```bash
python /Users/rafatsiddiqui/Downloads/Projects/Trust\ Safety\ Alignment/scripts/yt_to_summary.py "<YOUTUBE_URL>"
```

Or run yt-stt directly:

```bash
python /Users/rafatsiddiqui/Downloads/Projects/yt-stt/youtube_stt_screenshots.py "<YOUTUBE_URL>" \
  --transcript-only \
  --output "/path/to/Trust Safety Alignment/{Channel}/{Video Title}"
```

**Wait for completion** - this may take 5-15 minutes depending on video length.

### Step 4: Verify Transcript

Check that `transcript.txt` exists in the output folder and contains:
- Source URL at the top
- Full transcript text

### Step 5: Generate Summary

1. Read `transcript.txt` as the CORPUS
2. Read `PROMPT.md` for summarization instructions
3. Generate summary following the PROMPT.md template exactly:
   - Core Thesis
   - Mermaid Mindmap
   - Key Concepts with Inverse ELI scaling
   - Table (Dual Coding)
   - Contextual Connections
   - Active Recall (Feynman Test)
   - Further Reading (with verified URLs)

### Step 6: Verify Further Reading URLs

**CRITICAL**: For each URL in Further Reading:
1. Use web search to find candidate URLs
2. Use `curl` or `read_url` to fetch and verify HTTP 200
3. Only include working URLs with relevant content

### Step 7: Save Summary

Save the summary as `summary.md` in the same folder as `transcript.txt`.

### Step 8: Verify Cleanup

Confirm that no `.mp4`, `.mp3`, `.wav`, or `.webm` files remain in the output folder.

---

## Example Run

```bash
# User provides:
URL="https://www.youtube.com/watch?v=example"

# Agent runs:
python /Users/rafatsiddiqui/Downloads/Projects/Trust\ Safety\ Alignment/scripts/yt_to_summary.py "$URL"

# Agent then reads transcript.txt and generates summary.md using PROMPT.md
```

---

## Output Structure

```
Trust Safety Alignment/
├── {Channel}/
│   └── {Video Title}/
│       ├── transcript.txt    # Source URL + full transcript
│       └── summary.md        # Generated summary
└── PROMPT.md                 # Summarization instructions
```
