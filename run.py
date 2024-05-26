import argparse
import ffmpeg
from pathlib import Path


# Get args
parser = argparse.ArgumentParser(
    prog='dashcam-overlay',
    description='Process dashcam videos, overlaying rear-view camera video onto base front-view video.  Built for Viofo A139, but should work for arbitrary videos.'
)

parser.add_argument('base', help='Base video file.')
parser.add_argument('overlay', help='Video file to overlay on top.')
parser.add_argument(
    '-W', '--overlay-width',
    help='Width of overlay, in percentage of screen.',
    type=float,
    default=60
)
parser.add_argument(
    '-H', '--overlay-height', 
    help='Height of overlay, in percentage of screen.',
    type=float,
    default=35
)
parser.add_argument(
    '-p', '--overlay-position',
    help='Vertical position of overlay, in percentage of screen height.  0 is at top of screen, 100 is at bottom.',
    type=float,
    default=5
)
parser.add_argument(
    '-r', '--output-resolution',
    help='Resolution width of output video, in pixels.  Height will be inferred from video aspect ratio.',
    type=int,
    default=1080
)
parser.add_argument(
    '-Q', '--output-quality',
    help='FFmpeg quality preset for output video.  See https://trac.ffmpeg.org/wiki/Encode/H.264#Preset',
    default='veryfast'
)
parser.add_argument(
    '-m', '--mirror',
    help='Mirror video horizontally',
    default=False,
    action='store_true'
)
parser.add_argument(
    '-v', '--verbose',
    help='Verbose FFmpeg logging',
    default=False,
    action='store_true'
)
parser.add_argument(
    '-q', '--quiet',
    help='Minimal logging output.  Output files will be overwritten automatically if they already exist.',
    default=False,
    action='store_true'
)
parser.add_argument(
    '-o', '--output',
    help='File to save output to.  Will default to \'overlayed-<ffmpeg preset>-<base video path>\'.'
)

#TODO: Output file path option
args = parser.parse_args()


# Get video resolutions using ffmpeg,probe
base_video_stream = next((stream for stream in ffmpeg.probe(args.base)['streams'] if stream['codec_type'] == 'video'), None)
base_res = {'x': int(base_video_stream['width']), 'y': int(base_video_stream['height'])}
overlay_video_stream = next((stream for stream in ffmpeg.probe(args.overlay)['streams'] if stream['codec_type'] == 'video'), None)
overlay_res = {'x': int(overlay_video_stream['width']), 'y': int(overlay_video_stream['height'])}

if not args.quiet:
    print(f"Base video: \t'{args.base}' \t{base_res['x']}x{base_res['y']}")
    print(f"Overlay video: \t'{args.overlay}' \t{overlay_res['x']}x{overlay_res['y']}")


# Determine top-left corner position to place overlay
overlay_x_pos = (base_res['x'] / 2) - ( (base_res['x'] / 2) * (args.overlay_width / 100) )
overlay_y_pos = base_res['y'] * (args.overlay_position / 100)


# Determine how to crop overlay video
overlay_crop_origin_x = 0
overlay_crop_origin_y = (overlay_res['y'] / 2) - (overlay_res['y'] / 2) * (args.overlay_height / 100)
overlay_crop_width  = overlay_res['x']
overlay_crop_height = overlay_res['y'] - (overlay_crop_origin_y*2)


# Determine how to scale overlay video
overlay_scaled_width = base_res['x'] * (args.overlay_width / 100)


# Get the video files, and do cropping and scaling etc
base_file = ffmpeg.input(args.base)
overlay_file = (
    ffmpeg.input(args.overlay)
        .filter('crop', overlay_crop_width, overlay_crop_height, overlay_crop_origin_x, overlay_crop_origin_y)
        .filter('scale', overlay_scaled_width, -1)
    )

# Overlay the rear-view onto the base video
overlay_filter = (
    ffmpeg.overlay(base_file, overlay_file, x=overlay_x_pos, y=overlay_y_pos)
        .filter('scale', args.output_resolution, -1)
    )

if not args.quiet:
    print(f"Output resolution: {args.output_resolution}x{int(args.output_resolution * (overlay_res['y'] / overlay_res['x']))}, quality preset: {args.output_quality}")

# Apply mirror if requested
if args.mirror:
    if not args.quiet:
        print('Output will be mirrored.')

    overlay_filter = ffmpeg.hflip(overlay_filter)


# Prepare transcode
output_filename = args.output if args.output else 'overlayed-'+args.output_quality+'-'+args.base

if not args.quiet:
    print(f'Output will be saved to {output_filename}')

if not args.quiet and Path(output_filename).is_file() and input('File already exists.  Overwrite it? (y/N) - ').lower() != 'y':
    print('Not overwriting, bailing out.')  # We can't prompt in quiet mode, so overwrite
    exit(1)

command = ffmpeg.output(
    overlay_filter,
    base_file.audio, 
    output_filename,
    preset=args.output_quality
).overwrite_output()


# Run transcode
if not args.quiet:
    print('Running..')

command.run(capture_stdout=not args.verbose, capture_stderr=not args.verbose)

if not args.quiet:
    print('Done!')