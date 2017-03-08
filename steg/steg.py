from __future__ import print_function
from itertools import zip_longest

from bitarray import bitarray

import logging

logger = logging.getLogger(__name__)

null_byte = 8 * bitarray('0')


def message_to_bits(message):
    """Gets a BitStream from the input message string"""
    # convert to UTF-8 bytes
    message_bytes = message.encode(encoding='UTF-8')
    # Get the bits into a more accessible object
    message_bits = bitarray()
    message_bits.frombytes(message_bytes)
    # Append 0-byte at the end as a terminator
    message_bits.extend(null_byte)
    # Append any necessary 0 bits at the end to make the length divisible by 24. This ensures our message can be
    # evenly divided by 3, 4 and 8, which is helpful when dealing with 3 and 4 band images, and bytes.
    message_bits.extend((24 - (message_bits.length() % 24)) * bitarray('0'))

    if not message_bits[-8:] == null_byte:
        logger.error('Unable to convert message to bits with terminator.')
        raise IOError('Unable to convert message to bits with terminator.')
    else:
        logger.debug('Binary message: ' + message_bits.to01())
    # Convert to an easily consumable BitStream
    return message_bits


def image_can_fit_message(image, message):
    """Returns whether or not the given image can accommodate the given message"""
    # Get the number of bands per pixel. This is how many bytes are used to represent each pixel.
    # For example, an RGBA pixel will have 4 bands, giving us four pixels to update.

    pixel_data = image.getdata()
    num_bands = pixel_data.bands
    logger.debug('Found %s bands.', num_bands)

    # Get the number of pixels
    num_pixels = len(pixel_data)
    logger.debug('Found %s total pixels in the original image.', num_pixels)

    # Convert the message into bits
    message_bits = message_to_bits(message)
    num_message_bits = message_bits.length()
    logger.debug('The message is %s bits long', num_message_bits)

    # We can update one bit (the LSB) for each band of each pixel
    return num_message_bits <= (num_bands * num_pixels)


def convert_to_stego_image(image, message):
    """Returns the new pixel data of the image, with the message hidden inside"""

    # Get the number of bands per pixel. This is how many bytes are used to represent each pixel.
    old_pixel_data = image.getdata()
    num_bands = old_pixel_data.bands

    # Convert the message into bits
    message_bits = message_to_bits(message)

    # Will write our updated pixel data into this holder
    new_pixel_data = list()
    # Convert each of the old pixels into a stego pixel
    updated_bytes = convert_to_stego_bytes(_image_to_byte_stream(old_pixel_data), message_bits)

    # Fill the new pixel data with the updated pixels
    for new_pixel in _grouper(updated_bytes, num_bands, 0):
        new_pixel_data.append(new_pixel)

    logger.info("Inserted message into the image.")
    return new_pixel_data


def convert_to_stego_bytes(container_bytes, message_bits):
    """Converts the container bytes into stego bytes by updating its bytes' LSBs with the message bits"""

    # Reverse message_bits for easier popping
    message_bits.reverse()
    for container_byte in container_bytes:
        # If we're already consumed the stream, return the byte unaltered.
        if message_bits.length() <= 0:
            yield container_byte
        else:
            # Get the next bit in the message
            message_bit = message_bits.pop()
            # Update the container byte's LSB to be equal to our message's bit
            stego_byte = (container_byte & ~1) | message_bit
            yield stego_byte


def convert_from_stego_image(image):
    """Gets the message out of the image, or raises an IOError if no message could be found"""
    return convert_from_stego_bytes(_image_to_byte_stream(image.getdata()))


def convert_from_stego_bytes(container_bytes):
    """Extracts the message out of the container bytes, or raises an IOError if no message could be found"""
    all_LSBs = bitarray()
    # Convert it to an iterator just to be sure that we can call next on it to get each byte
    # This is safe if container_bytes is already an iterator.
    container_bytes = iter(container_bytes)

    # Need to get the LSB of each container byte, since it may be part of our message
    while not (all_LSBs[-8:] == null_byte and all_LSBs.length() % 8 == 0):
        pixel_byte = next(container_bytes)
        bit = (pixel_byte & 0x1)
        all_LSBs += [bit]

    logger.debug('All LSBs gathered: ' + all_LSBs.to01())

    # Find the 0-byte terminator we set when creating the image.
    terminator_pos = [pos for pos in all_LSBs.itersearch(null_byte) if pos % 8 == 0]

    # Make sure that we found our terminator.
    if len(terminator_pos) == 0:
        logger.error('Unable to find terminator. This may not be a stego image.')
        raise IOError('Unable to find terminator. This may not be a stego image.')

    # Get all the bits up to where the terminator starts
    message_bits = all_LSBs[:terminator_pos[0]]

    num_message_bits = message_bits.length()
    logger.debug('The message is %s bits long', num_message_bits)

    # Convert back to a string
    message = message_bits.tobytes().decode(encoding='UTF-8')

    return message


def _image_to_byte_stream(pixel_data):
    """A generator that yields each byte within each pixel of an image, in order"""
    for pixel in pixel_data:
        for pixel_byte in pixel:
            yield pixel_byte


def _grouper(iterable, n, fillvalue=None):
    """Collect data into fixed-length chunks or blocks
    grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    """
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)
