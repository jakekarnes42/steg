import click
from PIL import Image
from steg import steg


@click.group()
@click.version_option()
def cli():
    """A utility for concealing or revealing text into/from images"""


@cli.command()
@click.argument('message', type=click.File('rb'))
@click.argument('image', type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True))
@click.argument('output', type=click.Path(dir_okay=False, writable=True, resolve_path=True))
def conceal(message, image, output):
    """Attempts to hide MESSAGE into IMAGE, saves to OUTPUT.

    MESSAGE: A path to a file, whose contents will be imbedded into OUTPUT.
        If only '-' then text can be read from stdin and terminated with CTRL+D

    IMAGE: A path to an image file.

    OUTPUT: A path to where the new image should be written.

    """
    input_image = click.format_filename(image)
    output_image = click.format_filename(output)

    message_bytes = message.read()

    with Image.open(input_image) as im:
        if not (steg.image_can_fit_message(im, message_bytes)):
            raise ValueError('The message is cannot fit in the image.')

        new_pixel_data = steg.convert_to_stego_image(im, message_bytes)

        # Update and save image contents to file.
        im.putdata(new_pixel_data)
        im.save(output_image)


@cli.command()
@click.argument('image', type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True))
@click.argument('output', type=click.File('wb'))
def reveal(image, output):
    """Attempts to read from IMAGE to OUTPUT.

    IMAGE: A path to an image file which contains a concealed message.

    OUTPUT: A path to where the message content should be written.
        If only '-' then contents are written to stdout

    """
    input_image = click.format_filename(image)
    with Image.open(input_image) as im:
        decoded_message = steg.convert_from_stego_image(im)

    output.write(decoded_message)
    output.flush


if __name__ == '__main__':
    cli()
