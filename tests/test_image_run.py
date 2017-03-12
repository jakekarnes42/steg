import os
import logging

from PIL import Image

from steg import steg

import time

logging.basicConfig(level=os.environ.get("LOGLEVEL", "ERROR"))
logger = logging.getLogger(__name__)


def run():
    start_time = time.time()

    # Message to be encoded into image
    with open('text/sonnets.txt', 'r') as myfile:
        sonnets = myfile.read()
    with open('text/shakespeare-hamlet-25.txt', 'r') as myfile:
        hamlet = myfile.read()

    message = sonnets + hamlet

    out_formats = steg.LOSSLESS_IMG

    for out_format in out_formats:
        assert test_convert(message, out_format), "Format: " + out_format + " was unsuccessful!"
        print(out_format + " - PASS")

    print("--- %s seconds ---" % (time.time() - start_time))


def test_convert(message, out_format):
    outfile = 'images/halle_stego.' + out_format
    infile = 'images/halle.png'
    # Convert to Steg-image
    with Image.open(infile) as im:
        logger.info('Image info: Filename: %s ImageFormat: %s ImageSize: %s ImageMode: %s', infile, im.format,
                    ("%dx%d" % im.size), im.mode)

        if out_format in steg.RGB_ONLY:
            im = im.convert(mode="RGB")

        if not (steg.image_can_fit_message(im, message)):
            raise ValueError('The message is cannot fit in the image.')

        new_pixel_data = steg.convert_to_stego_image(im, message)

        # Update and save image contents to file.
        im.putdata(new_pixel_data)
        im.save(outfile, lossless=True)

    # Convert back
    with Image.open(outfile) as im:
        logger.info('Image info: Filename: %s ImageFormat: %s ImageSize: %s ImageMode: %s', infile, im.format,
                    ("%dx%d" % im.size), im.mode)

        decoded_bytes = steg.convert_from_stego_image(im)

    decoded_message = decoded_bytes.decode(encoding="UTF-8")
    return decoded_message.endswith('ordnance is shot off]\n')


if __name__ == '__main__':
    run()
