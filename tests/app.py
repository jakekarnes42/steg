import os
import logging

from PIL import Image

from steg import steg

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
logger = logging.getLogger(__name__)

infile = 'images/halle.png'

outfile = 'images/halle_out.png'


# Message to be encoded into image
with open('text/sonnets.txt', 'r') as myfile:
   message=myfile.read()

# Convert to Steg-image
with Image.open(infile) as im:
    logger.info('Image info: Filename: %s ImageFormat: %s ImageSize: %s ImageMode: %s', infile, im.format,
                ("%dx%d" % im.size), im.mode)

    if not (steg.image_can_fit_message(im, message)):
        raise ValueError('The message is cannot fit in the image.')

    new_pixel_data = steg.convert_to_stego_image(im, message)

    # Update and save image contents to file.
    im.putdata(new_pixel_data)
    im.save(outfile)  # Get message back from newly created Steg-image

# Convert back
with Image.open(outfile) as im:
    logger.info('Image info: Filename: %s ImageFormat: %s ImageSize: %s ImageMode: %s', infile, im.format,
                ("%dx%d" % im.size), im.mode)

    decoded_message = steg.convert_from_stego_image(im)

    print(decoded_message)
