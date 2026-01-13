#!/usr/bin/env python3
"""
Video Processor: Black out video, add text overlay, keep original audio
Usage: python video_processor.py input.mp4 output.mp4 "Your text here"
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path


def find_ffmpeg():
    """Find FFmpeg executable, checking common locations"""
    # Try ffmpeg in PATH first
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        return 'ffmpeg'
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # On Windows, check WinGet installation location
    if sys.platform == 'win32':
        import glob
        winget_pattern = os.path.join(
            os.environ.get('LOCALAPPDATA', ''),
            'Microsoft', 'WinGet', 'Packages',
            'Gyan.FFmpeg*', 'ffmpeg-*', 'bin', 'ffmpeg.exe'
        )
        matches = glob.glob(winget_pattern)
        if matches:
            return matches[0]
        
        # Check Program Files
        program_files_locations = [
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
            r'C:\ffmpeg\bin\ffmpeg.exe',
        ]
        for location in program_files_locations:
            if os.path.exists(location):
                return location
    
    return None


def check_ffmpeg():
    """Check if FFmpeg is installed and accessible"""
    ffmpeg_path = find_ffmpeg()
    
    if ffmpeg_path is None:
        print("\n✗ ERROR: FFmpeg not found!")
        print("\nFFmpeg is required but not installed or not in your PATH.")
        print("\nInstallation instructions:")
        print("  Windows: ")
        print("    1. Download from https://ffmpeg.org/download.html")
        print("    2. Or use: winget install ffmpeg")
        print("    3. Or use chocolatey: choco install ffmpeg")
        print("  Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("  macOS: brew install ffmpeg")
        return None
    
    try:
        result = subprocess.run(
            [ffmpeg_path, '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        print(f"✓ FFmpeg found: {ffmpeg_path}")
        return ffmpeg_path
    except subprocess.TimeoutExpired:
        print("\n✗ ERROR: FFmpeg check timed out")
        return None
    except Exception as e:
        print(f"\n✗ ERROR checking FFmpeg: {e}")
        return None


def validate_input_file(input_file):
    """Validate that input file exists and is readable"""
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"\n✗ ERROR: Input file not found: {input_file}")
        print(f"\nCurrent directory: {os.getcwd()}")
        print("\nFiles in current directory:")
        try:
            for f in os.listdir('.'):
                if f.endswith(('.mp4', '.MP4', '.avi', '.mov')):
                    print(f"  - {f}")
        except Exception as e:
            print(f"  Could not list files: {e}")
        return False
    
    if not input_path.is_file():
        print(f"\n✗ ERROR: Input path is not a file: {input_file}")
        return False
    
    if input_path.stat().st_size == 0:
        print(f"\n✗ ERROR: Input file is empty: {input_file}")
        return False
    
    print(f"✓ Input file found: {input_file} ({input_path.stat().st_size:,} bytes)")
    return True


def validate_output_path(output_file):
    """Validate that output path is writable"""
    output_path = Path(output_file)
    
    # Check if parent directory exists and is writable
    parent_dir = output_path.parent
    if not parent_dir.exists():
        print(f"\n✗ ERROR: Output directory does not exist: {parent_dir}")
        return False
    
    if not os.access(parent_dir, os.W_OK):
        print(f"\n✗ ERROR: No write permission in output directory: {parent_dir}")
        return False
    
    # Warn if output file already exists
    if output_path.exists():
        print(f"⚠ Warning: Output file already exists and will be overwritten: {output_file}")
    
    print(f"✓ Output path is valid: {output_file}")
    return True


def process_video(input_file, output_file, text, font_size=48, font_color='white'):
    """
    Process video: make video black, add text overlay, preserve audio
    
    Args:
        input_file: Path to input MP4 file
        output_file: Path to output MP4 file
        text: Text to display on the video
        font_size: Font size for the text (default: 48)
        font_color: Color of the text (default: 'white')
    """
    
    print("\n" + "="*60)
    print("VIDEO PROCESSING STARTED")
    print("="*60)
    
    # Validate inputs
    ffmpeg_path = check_ffmpeg()
    if not ffmpeg_path:
        return False
    
    if not validate_input_file(input_file):
        return False
    
    if not validate_output_path(output_file):
        return False
    
    # Escape text for FFmpeg filter
    # Replace special characters that might cause issues
    escaped_text = text.replace("'", "'\\\\\\''").replace(":", "\\:")
    
    # Build FFmpeg command with corrected filter syntax
    # We need to get video dimensions first, then create black overlay
    command = [
        ffmpeg_path,
        '-i', input_file,
        '-vf', (
            # Create black video matching input dimensions and overlay it
            f"drawbox=color=black@1.0:t=fill,"
            f"drawtext="
            f"text='{escaped_text}':"
            f"fontsize={font_size}:"
            f"fontcolor={font_color}:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2"
        ),
        '-c:a', 'copy',  # Copy audio without re-encoding
        '-y',  # Overwrite output file if it exists
        output_file
    ]
    
    print(f"\n📹 Input: {input_file}")
    print(f"💾 Output: {output_file}")
    print(f"📝 Text: '{text}'")
    print(f"🎨 Font: {font_size}pt {font_color}")
    print("\nProcessing video (this may take a moment)...")
    
    try:
        # Run FFmpeg command with real-time output
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Collect all output
        all_output = []
        last_progress = ""
        
        for line in process.stdout:
            all_output.append(line)
            # FFmpeg outputs progress to stderr, which we've redirected to stdout
            if "time=" in line or "frame=" in line:
                # Update progress on same line
                print(f"\r{line.strip()[:80]}", end='', flush=True)
                last_progress = line
        
        process.wait()
        
        if process.returncode != 0:
            print(f"\n\n✗ FFmpeg failed with return code {process.returncode}")
            print("\n" + "="*60)
            print("FFMPEG ERROR OUTPUT:")
            print("="*60)
            # Show last 30 lines or all output if less
            error_lines = all_output[-30:] if len(all_output) > 30 else all_output
            for line in error_lines:
                print(line.rstrip())
            print("="*60)
            return False
        
        # Verify output file was created
        if not os.path.exists(output_file):
            print("\n\n✗ ERROR: Output file was not created")
            return False
        
        output_size = os.path.getsize(output_file)
        if output_size == 0:
            print("\n\n✗ ERROR: Output file is empty")
            return False
        
        print("\n\n" + "="*60)
        print("✓ VIDEO PROCESSING COMPLETE!")
        print("="*60)
        print(f"Output file: {output_file}")
        print(f"File size: {output_size:,} bytes")
        print(f"Location: {os.path.abspath(output_file)}")
        return True
        
    except subprocess.TimeoutExpired:
        print("\n\n✗ ERROR: FFmpeg process timed out")
        return False
    except Exception as e:
        print(f"\n\n✗ ERROR during processing: {type(e).__name__}: {e}")
        import traceback
        print("\nFull error details:")
        traceback.print_exc()
        return False


def main():
    print("="*60)
    print("VIDEO PROCESSOR - Black Video with Text Overlay")
    print("="*60)
    
    parser = argparse.ArgumentParser(
        description='Black out video, add text overlay, preserve audio',
        epilog='Example: python video_processor.py input.mp4 output.mp4 "Hello World"'
    )
    parser.add_argument(
        'input',
        help='Input MP4 file path'
    )
    parser.add_argument(
        'output',
        help='Output MP4 file path'
    )
    parser.add_argument(
        'text',
        help='Text to display on the video'
    )
    parser.add_argument(
        '--font-size',
        type=int,
        default=48,
        help='Font size for text (default: 48)'
    )
    parser.add_argument(
        '--font-color',
        default='white',
        help='Font color (default: white)'
    )
    
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse calls sys.exit on error, catch it to provide better info
        if e.code != 0:
            print("\n⚠ Tip: Make sure to provide all required arguments:")
            print('  python video_processor.py input.mp4 output.mp4 "Your text"')
        sys.exit(e.code)
    
    try:
        success = process_video(
            args.input,
            args.output,
            args.text,
            args.font_size,
            args.font_color
        )
        
        if success:
            print("\n🎉 Success! Your video is ready.")
            sys.exit(0)
        else:
            print("\n❌ Processing failed. Please check the errors above.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠ Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ UNEXPECTED ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()