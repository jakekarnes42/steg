import os
import logging

from pydub import AudioSegment

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

    out_formats = steg.LOSSLESS_AUDIO

    for out_format in out_formats:
        if test_convert(message, out_format):
            print(out_format + " - PASS")
        else:
            raise AssertionError("Format: " + out_format + " was unsuccessful!")

    print("--- %s seconds ---" % (time.time() - start_time))


def test_convert(message, out_format):
    outfile = 'audio/bach_stego.' + out_format
    infile = 'audio/bach_standard.wav'
    # Convert to Steg-audio
    wav_audio = AudioSegment.from_file(infile, format="wav")
    logger.info('Audio info: Filename: %s FrameCount: %s FrameWidth: %s SampleWidth: %s', infile,
                wav_audio.frame_count(),
                wav_audio.frame_width, wav_audio.sample_width)
    if not steg.audio_can_fit_message(wav_audio, message):
        raise ValueError('The message is cannot fit in the audio.')
    new_audio_data = steg.convert_to_stego_audio(wav_audio, message)
    new_audio_segment = AudioSegment(data=new_audio_data, sample_width=wav_audio.sample_width,
                                     frame_rate=wav_audio.frame_rate, channels=wav_audio.channels)
    new_audio_segment.export(outfile, format=out_format)
    # Convert back
    steg_audio = AudioSegment.from_file(outfile, format=out_format)
    logger.info('Audio info: Filename: %s FrameCount: %s FrameWidth: %s SampleWidth: %s', infile,
                steg_audio.frame_count(),
                steg_audio.frame_width, steg_audio.sample_width)
    decoded_bytes = steg.convert_from_stego_audio(steg_audio)
    decoded_message = decoded_bytes.decode(encoding="UTF-8")
    return decoded_message.endswith('ordnance is shot off]\n')


if __name__ == '__main__':
    run()
