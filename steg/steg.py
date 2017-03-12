from __future__ import print_function
from itertools import zip_longest, chain
import sys
from bitarray import bitarray

import logging

logger = logging.getLogger(__name__)

ENDIAN = sys.byteorder
# In little endian format, the LSB is the first bit. In big endian format, the LSB is the last bit
LSB_INDEX = 0 if ENDIAN == 'little' else -1


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
    updated_bytes = convert_to_stego_samples(_image_to_sample_stream(old_pixel_data), message_bits)

    # Fill the new pixel data with the updated pixels
    for new_pixel in _samples_to_pixels(updated_bytes, num_bands, 0):
        new_pixel_data.append(new_pixel)

    logger.info("Inserted message into the image.")
    return new_pixel_data


def convert_to_stego_samples(container_samples, message_bits):
    """Converts the container samples into stego samples by updating its samples' LSBs with the message bits"""
    container_samples = iter(container_samples)

    # Insert each message bit into the LSB of a container sample
    for message_bit in iter(message_bits):
        container_sample = next(container_samples)
        # Update the container samples's LSB to be equal to our message's bit
        container_sample[LSB_INDEX] = message_bit
        yield container_sample

    # Now that we're out of message bits, just return the rest of the container samples as-is
    yield from container_samples


def convert_from_stego_image(image):
    """Gets the message out of the image, or raises an IOError if no message could be found"""
    return convert_from_stego_samples(_image_to_sample_stream(image.getdata()))


def convert_from_stego_samples(container_samples):
    """Extracts the message (as bytes) out of the container samples"""

    # Convert it to an iterator just to be sure that we can call next on it to get each sample
    # This is safe if container_samples is already an iterator.
    container_samples = iter(container_samples)

    # Get the first 64 bits, which will tell us how many bytes to read.
    message_length_bits = bitarray(64, endian=ENDIAN)
    for index in range(64):
        pixel_sample = next(container_samples)
        message_length_bits[index] = pixel_sample[LSB_INDEX]

    # Convert bits into an integer
    logger.debug('message_length_bits: %s', message_length_bits.to01())
    message_length = int.from_bytes(message_length_bits.tobytes(), byteorder=ENDIAN)
    logger.debug('Expecting message to be %s bits long', message_length)

    # Read message_length number of bits into our bit array.
    message_bits = bitarray(message_length, endian=ENDIAN)
    for index in range(message_length):
        pixel_sample = next(container_samples)
        message_bits[index] = pixel_sample[LSB_INDEX]

    num_message_bits = message_bits.length()
    logger.debug('The message is %s bits long', num_message_bits)

    # Convert back to bytes
    message = message_bits.tobytes()

    return message


def _image_to_sample_stream(pixel_data):
    """A generator that yields each byte (as a bitarray) within each pixel of an image, in order"""
    all_bytes = bytes(chain.from_iterable(pixel_data))
    all_bits = bitarray(endian=ENDIAN)
    all_bits.frombytes(all_bytes)

    for index in range(0, all_bits.length(), 8):
        pixel_bits = all_bits[index:(index + 8)]
        yield pixel_bits


def _samples_to_pixels(sample_stream, n, fillvalue=None):
    # Need to convert each sample from a bitarray to a single byte
    samples = [map(lambda x: x.tobytes()[0], iter(sample_stream))] * n

    return zip_longest(*samples, fillvalue=fillvalue)
