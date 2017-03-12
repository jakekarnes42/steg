from __future__ import print_function
from itertools import zip_longest, chain
import sys
from bitarray import bitarray

import logging

logger = logging.getLogger(__name__)

# This allows us to use consistent endianness throughout the program
ENDIAN = sys.byteorder
# In little endian format, the LSB is the first bit. In big endian format, the LSB is the last bit
LSB_INDEX = 0 if ENDIAN == 'little' else -1

# Lossless audio codecs that are valid for output
LOSSLESS_AUDIO = set(["aiff", "ast", "au", "caf", "f32be", "f32le", "f64be", "f64le", "flac", "ircam", "s16be", "s16le",
                      "s24be", "s24le", "s32be", "s32le", "smjpeg", "sox", "u16be", "u16le", "u24be", "u24le", "u32be",
                      "u32le", "voc", "w64", "wav", "wv"])
# Lossless image formats that are valid for output
LOSSLESS_IMG = set(["bmp", "im", "j2k", "pbm", "pcx", "pgm", "ppm", "png", "tiff", "tif", "webp"])

# Image formats that need the input image converted to RGB before processing. Otherwise they'll lose the alpha channel
RGB_ONLY = set(["bmp", "pcx", "pbm", "pgm", "ppm"])


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


def audio_can_fit_message(audio, message):
    """Returns whether or not the given audio can accommodate the given message"""

    # Convert the message into bits
    message_bits = message_to_bits(message)
    num_message_bits = message_bits.length()
    logger.info('The message is %s bits long', num_message_bits)

    # Get audio info
    frame_count = audio.frame_count()
    channels = audio.channels

    # We can fit one bit of message, per frame, per channel.
    return num_message_bits <= (frame_count * channels)


def convert_to_stego_image(image, message):
    """Returns the new pixel data of the image, with the message hidden inside"""

    # Get the number of bands per pixel. This is how many bytes are used to represent each pixel.
    old_pixel_data = image.getdata()
    num_bands = old_pixel_data.bands

    # Convert the message to bits
    message_bits = message_to_bits(message)

    # Will write our updated pixel data into this holder
    new_pixel_data = list()
    # Convert each of the old pixels into a stego pixel, and get the resulting bytes
    updated_bytes = convert_to_stego_bitarray(_image_to_bitarray(old_pixel_data), message_bits,
                                              _get_bits_per_pixel(image)).tobytes()

    # Fill the new pixel data with the updated pixels
    for new_pixel in _grouper(updated_bytes, num_bands, 0):
        new_pixel_data.append(new_pixel)

    logger.info("Inserted message into the image.")
    return new_pixel_data


def _get_bits_per_pixel(image):
    bits_per_pixel = 8  # default 8-bit pixels
    if '1' in image.mode:
        raise ValueError("Unable to convert 1-bit images")
    elif "I" in image.mode or "F" in image.mode:
        bits_per_pixel = 32  # 32-bit pixels

    return bits_per_pixel


def convert_to_stego_audio(audio, message):
    """Returns the new sample data of the audio, with the message hidden inside"""

    # Convert the message into bits
    message_bits = message_to_bits(message)

    old_audio_data = audio.raw_data
    bits_per_sample = audio.sample_width * 8

    # Convert each of the old samples into a stego sample
    new_audio_data = convert_to_stego_bitarray(_audio_to_bitarray(old_audio_data), message_bits, bits_per_sample)

    logger.info("Inserted message into the audio.")
    return new_audio_data.tobytes()


def convert_to_stego_bitarray(container_bitarray, message_bits, bits_per_sample):
    """Converts the container bitarray by updating its samples' LSBs with the message bits"""
    lsb_offset = 0 if ENDIAN == 'little' else (bits_per_sample - 1)
    end = (message_bits.length() * bits_per_sample)

    # Update the LSBs in the bitarray through slice assignment
    container_bitarray[lsb_offset:end:bits_per_sample] = message_bits

    return container_bitarray


def convert_from_stego_image(image):
    """Gets the message out of the image"""
    return convert_from_stego_bitarray(_image_to_bitarray(image.getdata()), _get_bits_per_pixel(image))


def convert_from_stego_audio(audio):
    """Gets the message out of the image"""
    bits_per_sample = audio.sample_width * 8
    return convert_from_stego_bitarray(_audio_to_bitarray(audio.raw_data), bits_per_sample)


def convert_from_stego_bitarray(container_bitarray, bits_per_sample):
    """Extracts the message (as bytes) out of the container bitarray"""

    lsb_offset = 0 if ENDIAN == 'little' else (bits_per_sample - 1)
    # Gets all LSBs as a slice
    all_lsbs = container_bitarray[lsb_offset::bits_per_sample]

    ## Get the first 64 bits, which will tell us how many bits are part of the message.
    message_length_bits = all_lsbs[:64]

    # Convert bits into an integer
    logger.debug('message_length_bits: %s', message_length_bits.to01())
    message_length = int.from_bytes(message_length_bits.tobytes(), byteorder=ENDIAN)
    logger.debug('Expecting message to be %s bits long', message_length)

    # Get the message bits which come after the 64 length bits
    message_bits = all_lsbs[64:message_length + 64]

    num_message_bits = message_bits.length()
    logger.debug('The message is %s bits long', num_message_bits)

    # Convert back to bytes
    message = message_bits.tobytes()

    return message


def _image_to_bitarray(pixel_data):
    """Converts the pixel data from the image into a large bitarray"""
    all_bytes = bytes(chain.from_iterable(pixel_data))
    all_bits = bitarray(endian=ENDIAN)
    all_bits.frombytes(all_bytes)
    return all_bits


def _audio_to_bitarray(audio_data):
    """Converts the audio data into a large bitarray"""
    all_bits = bitarray(endian=ENDIAN)
    all_bits.frombytes(audio_data)
    return all_bits


def _grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)
