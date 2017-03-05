import os
import logging

from PIL import Image

from steg import image_can_fit_message, convert_to_stego_image, convert_from_stego_image

logging.basicConfig(level=os.environ.get("LOGLEVEL", "ERROR"))
logger = logging.getLogger(__name__)

infile = 'images/halle.png'

outfile = 'images/halle_out.png'

# Message to be encoded into image
message = 'lol balls'

# Convert to Steg-image
try:
    with Image.open(infile) as im:
        logger.info('Image info: Filename: %s ImageFormat: %s ImageSize: %s ImageMode: %s', infile, im.format,
                    ("%dx%d" % im.size), im.mode)

        if not (image_can_fit_message(im, message)):
            raise ValueError('The message is cannot fit in the image.')

        new_pixel_data = convert_to_stego_image(im, message)

        # Update and save image contents to file.
        im.putdata(new_pixel_data)
        im.save(outfile)

except IOError:
    pass

# Get message back from newly created Steg-image
try:
    with Image.open(outfile) as im:
        logger.info('Image info: Filename: %s ImageFormat: %s ImageSize: %s ImageMode: %s', infile, im.format,
                    ("%dx%d" % im.size), im.mode)

        decoded_message = convert_from_stego_image(im)

        print(decoded_message)

except IOError:
    pass
