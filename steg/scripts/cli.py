import click
from PIL import Image
from steg import steg
from os import path
from pydub import AudioSegment

audio_formats = []


@click.group()
@click.version_option()
def cli():
    """A utility for concealing or revealing text into/from audio/image files"""


@cli.command()
@click.argument('message', type=click.File('rb'))
@click.argument('container', type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True))
@click.argument('output', type=click.Path(dir_okay=False, writable=True, resolve_path=True))
def conceal(message, container, output):
    """Attempts to hide MESSAGE into CONTAINER, saves to OUTPUT.

    MESSAGE: A path to a file, whose contents will be imbedded into OUTPUT.
        If only '-' then text can be read from stdin and terminated with CTRL+D

    IMAGE: A path to an image or audio file.

    OUTPUT: A path to where the new image or audio should be written.

    Supported output formats:
    AUDIO = "aiff", "ast", "au", "caf", "f32be", "f32le", "f64be", "f64le", "flac", "ircam", "s16be", "s16le",
                      "s24be", "s24le", "s32be", "s32le", "smjpeg", "sox", "u16be", "u16le", "u24be", "u24le", "u32be",
                      "u32le", "voc", "w64", "wav", "wv"
    IMAGE = "bmp", "im","j2k", "pbm", "pcx",  "pgm", "ppm", "png", "tiff", "tif", "webp"

    """
    input_file = click.format_filename(container)
    input_extension = path.splitext(input_file)[1][1:].lower()
    output_file = click.format_filename(output)
    output_extension = path.splitext(output_file)[1][1:].lower()

    message_bytes = message.read()

    if output_extension in steg.LOSSLESS_AUDIO:
        conceal_audio(input_file, input_extension, output_file, output_extension, message_bytes)
    elif output_extension in steg.LOSSLESS_IMG:
        conceal_image(input_file, input_extension, output_file, output_extension, message_bytes)
    else:
        raise ValueError("Cannot use given output format: " + output_extension)


def conceal_audio(input_file, input_extension, output_file, output_extension, message_bytes):
    input_audio = AudioSegment.from_file(input_file, format=input_extension)

    if not steg.audio_can_fit_message(input_audio, message_bytes):
        raise ValueError('The message is cannot fit in the audio.')

    new_audio_data = steg.convert_to_stego_audio(input_audio, message_bytes)
    new_audio_segment = AudioSegment(data=new_audio_data, sample_width=input_audio.sample_width,
                                     frame_rate=input_audio.frame_rate, channels=input_audio.channels)
    new_audio_segment.export(output_file, format=output_extension)


def conceal_image(input_file, input_extension, output_file, output_extension, message_bytes):
    with Image.open(input_file) as im:
        if output_extension in steg.RGB_ONLY:
            im = im.convert(mode="RGB")

        if not (steg.image_can_fit_message(im, message_bytes)):
            raise ValueError('The message is cannot fit in the image.')

        new_pixel_data = steg.convert_to_stego_image(im, message_bytes)

        # Update and save image contents to file.
        im.putdata(new_pixel_data)
        im.save(output_file, lossless=True)


@cli.command()
@click.argument('input', type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True))
@click.argument('output', type=click.File('wb'))
def reveal(input, output):
    """Attempts to read from INPUT to OUTPUT.

    INPUT: A path to an image or audio file which contains a concealed message.

    OUTPUT: A path to where the message content should be written.
        If only '-' then contents are written to stdout

    """
    input_file = click.format_filename(input)
    input_extension = path.splitext(input_file)[1][1:].lower()

    if input_extension in steg.LOSSLESS_AUDIO:
        steg_audio = AudioSegment.from_file(input_file, format=input_extension)
        decoded_message = steg.convert_from_stego_audio(steg_audio)
    elif input_extension in steg.LOSSLESS_IMG:
        with Image.open(input_file) as im:
            decoded_message = steg.convert_from_stego_image(im)
    else:
        raise ValueError("Cannot use given input format: " + input_extension)

    output.write(decoded_message)
    output.flush


if __name__ == '__main__':
    cli()
