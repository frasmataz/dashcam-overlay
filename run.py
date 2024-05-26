import sys
import argparse
import ffmpeg


# Get args
parser = argparse.ArgumentParser(
    prog='dashcam-overlay',
    description='Process dashcam videos, overlaying rear-view camera video onto base front-view video.  Built for Viofo A139, but should work for arbitrary videos.'
)

base_video_filename = sys.argv[1]    # Get path to base video file
overlay_video_filename = sys.argv[2] 
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
    '-q', '--output-quality',
    help='FFmpeg quality preset for output video.  See https://trac.ffmpeg.org/wiki/Encode/H.264#Preset',
    default='veryfast'
)
parser.add_argument(
    '-m', '--mirror',
    help='Mirror video horizontally',
    default=False,
    action='store_true'
) #TODO: actually implement this

#TODO: Output file path option
args = parser.parse_args()


# Get video resolutions using ffmpeg,probe
base_video_stream = next((stream for stream in ffmpeg.probe(base_video_filename)['streams'] if stream['codec_type'] == 'video'), None)
base_res = {'x': int(base_video_stream['width']), 'y': int(base_video_stream['height'])}

overlay_video_stream = next((stream for stream in ffmpeg.probe(overlay_video_filename)['streams'] if stream['codec_type'] == 'video'), None)
overlay_res = {'x': int(overlay_video_stream['width']), 'y': int(overlay_video_stream['height'])}


# Determine top-left corner position to place overlay
overlay_x_pos = (base_res['x'] / 2) - ( (base_res['x'] / 2) * (args.overlay_width / 100) )
overlay_y_pos = base_res['y'] * (args.overlay_position / 100)


# Determine how to crop overlay video
overlay_crop_origin_x = 0
overlay_crop_origin_y = (overlay_res['y'] / 2) - (overlay_res['y'] / 2) * (args.overlay_height / 100)
overlay_crop_width = overlay_res['x']
overlay_crop_height = overlay_res['y'] - (overlay_crop_origin_y*2)


# Determine how to scale overlay video
overlay_scaled_width = base_res['x'] * (args.overlay_width / 100)


# Get the video files, and do cropping and scaling etc
base_file = ffmpeg.input(base_video_filename)
overlay_file = (
    ffmpeg.input(overlay_video_filename)
        .filter('crop', overlay_crop_width, overlay_crop_height, overlay_crop_origin_x, overlay_crop_origin_y)
        .filter('scale', overlay_scaled_width, -1)
    )


# Overlay the rear-view onto the base video
overlay_filter = (
    ffmpeg.overlay(base_file, overlay_file, x=overlay_x_pos, y=overlay_y_pos)
        .filter('scale', args.output_resolution, -1)
    )


# Run transcode
command = ffmpeg.output(
    overlay_filter, 
    base_file.audio, 
    'overlayed-'+args.output_quality+base_video_filename, 
    preset=args.output_quality
)

command.run(capture_stdout=False, capture_stderr=False)