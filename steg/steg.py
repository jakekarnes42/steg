from __future__ import print_function
from itertools import zip_longest

from bitarray import bitarray

import logging

logger = logging.getLogger(__name__)

ENDIAN = 'big'


def message_to_bits(message):
    """Gets a BitStream from the input message string"""

    # If not already bytes, convert to UTF-8 bytes
    if not isinstance(message, (bytes, bytearray)):
        message_bytes = message.encode(encoding='UTF-8')
    else:
        message_bytes = message

    # Get the bits into a more accessible object
    message_bits = bitarray(endian=ENDIAN)
    message_bits.frombytes(message_bytes)

    num_message_bits = message_bits.length()
    logger.debug('The message is %s bits long', num_message_bits)

    # Create a 64 bitarray to hold the data length
    length_bits = bitarray(endian=ENDIAN)
    length_bits.frombytes(num_message_bits.to_bytes(8, byteorder=ENDIAN))
    logger.debug('message_length_bits: %s', length_bits.to01())

    # Create final bitarray that is the length + the message
    complete_bits = bitarray(endian=ENDIAN)
    complete_bits.extend(length_bits)
    complete_bits.extend(message_bits)

    return complete_bits


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
    logger.info('The message is %s bits long', num_message_bits)

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
    container_bytes = iter(container_bytes)

    # Insert each message bit into the LSB of a container byte
    for message_bit in iter(message_bits):
        container_byte = next(container_bytes)
        # Update the container byte's LSB to be equal to our message's bit
        stego_byte = (container_byte & ~1) | message_bit
        yield stego_byte

    # Now that we're out of message bits, just return the rest of the container bytes as-is
    yield from container_bytes


def convert_from_stego_image(image):
    """Gets the message out of the image, or raises an IOError if no message could be found"""
    return convert_from_stego_bytes(_image_to_byte_stream(image.getdata()))


def convert_from_stego_bytes(container_bytes):
    """Extracts the message (as bytes) out of the container bytes"""

    # Convert it to an iterator just to be sure that we can call next on it to get each byte
    # This is safe if container_bytes is already an iterator.
    container_bytes = iter(container_bytes)

    # Get the first 64 bits, which will tell us how many bytes to read.
    message_length_bits = bitarray(64, endian=ENDIAN)
    for index in range(64):
        pixel_byte = next(container_bytes)
        bit = (pixel_byte & 0x1)
        message_length_bits[index] = bit

    # Convert bits into an integer
    logger.debug('message_length_bits: %s', message_length_bits.to01())
    message_length = int.from_bytes(message_length_bits.tobytes(), byteorder=ENDIAN)
    logger.debug('Expecting message to be %s bits long', message_length)

    # Read message_length number of bits into our bit array.
    message_bits = bitarray(message_length, endian=ENDIAN)
    for index in range(message_length):
        pixel_byte = next(container_bytes)
        bit = (pixel_byte & 0x1)
        message_bits[index] = bit

    num_message_bits = message_bits.length()
    logger.debug('The message is %s bits long', num_message_bits)

    # Convert back to bytes
    message = message_bits.tobytes()

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
