#!/bin/bash

# This script converts the demo.webm video to lower resolutions for mobile and tablet devices
# Requires ffmpeg to be installed

# Source video path
SOURCE_VIDEO="src/static/vid/demo.webm"

# Output paths
MEDIUM_VIDEO="src/static/vid/demo_medium.webm"
MOBILE_VIDEO="src/static/vid/demo_mobile.webm"

# Check if source video exists
if [ ! -f "$SOURCE_VIDEO" ]; then
    echo "Error: Source video not found at $SOURCE_VIDEO"
    exit 1
fi

# Create medium resolution (720p) for tablets
echo "Creating medium resolution video for tablets..."
ffmpeg -i "$SOURCE_VIDEO" -vf "scale=1280:720" -c:v libvpx-vp9 -crf 30 -b:v 1M -c:a libopus "$MEDIUM_VIDEO"

# Create low resolution (480p) for mobile
echo "Creating low resolution video for mobile..."
ffmpeg -i "$SOURCE_VIDEO" -vf "scale=854:480" -c:v libvpx-vp9 -crf 33 -b:v 600k -c:a libopus "$MOBILE_VIDEO"

echo "Video conversion complete!"
echo "Original video: $SOURCE_VIDEO"
echo "Medium resolution (720p): $MEDIUM_VIDEO"
echo "Mobile resolution (480p): $MOBILE_VIDEO"