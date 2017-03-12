# Steg Project
This is an exploration into Steganography using Python. Messages can be hidden within audio or image files.

## Supported formats
Many image/audio formats should work as input files. The actual decoding is delegated to the [Pillow](https://pillow.readthedocs.io/en/3.4.x/handbook/image-file-formats.html) library for images, and [ffmpeg](https://www.ffmpeg.org/ffmpeg-formats.html) for audio. Any of their input formats should be acceptable. 

That being said, only lossless output formats can be utilized. If lossy compression were used, the least significant bits (LSBs) where the message is stored could be squashed. 

### Supported image output formats:
```
"bmp", "im", "j2k", "pbm", "pcx", "pgm", "ppm", "png", "tiff", "tif", "webp" 
```

### Supported audio output formats:
```
"aiff", "ast", "au", "caf", "f32be", "f32le", "f64be", "f64le", "flac", "ircam", "s16be", "s16le", "s24be", "s24le", "s32be", "s32le", "smjpeg", "sox", "u16be", "u16le", "u24be", "u24le", "u32be","u32le", "voc", "w64", "wav", "wv"
```

## Command Line Interface
First, run the setuptools to prepare the executable.
```
sudo -H pip install --editable .
```

### Reading and writing plain text
Text can be embedded through stdin, and terminated with CTRL+D
```
steg conceal - tests/images/halle.png shakey_halle.png
This is the text I want to hide in my image.
```
It can then be read back:
```
steg reveal shakey_halle.png -
This is the text I want to hide in my image.
```

### Reading and writing files
Files can be handled in a similar fashion. The following embeds all the works of Shakespeare (compressed) into an image:
```
steg conceal tests/text/shakespeare_all.bz2 tests/images/halle.png shakey_halle.png
```
It can then be extracted back out:
```
steg reveal shakey_halle.png shakespeare_extracted.bz2
```

### Fun with pipes
Since the CLI reads from standard input, data can be piped through other utilies which perform other transformations. The following encrypts and compresses the text "this is some text" and conceals it in an image.
```
echo this is some text | gzip | gpg -c --passphrase my_password | steg conceal - tests/images/halle.png shakey_halle.png
```
To recover the plain text, execute the following:
```
steg reveal shakey_halle.png - | gpg -d -q --passphrase my_password | gzip -d
```

### Audio files supported as well
All of the above examples work equally well with audio files as well. Here's the previous example using .wav files
```
echo this is some text | gzip | gpg -c --passphrase my_password | steg conceal - tests/audio/bach_standard.wav bach_stego.wav
```
To recover the plain text, execute the following:
```
steg reveal bach_stego.wav - | gpg -d -q --passphrase my_password | gzip -d
```



## Dev Env:
    Ubuntu 16.04 LTS

## Setup:
    Python Dev Dependencies:
        sudo apt install python3-dev python3-setuptools python-pip
        pip install --upgrade pip

    Pillow Imaging Dependencies
        sudo apt install libtiff5-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.5-dev tk8.5-dev python-tk

    Pydub Audio Dependencies
        sudo apt install ffmpeg libavcodec-extra

## Project Dependencies:
If unable to setuptools or the requirements.txt for some reason:
```
pip install Pillow
pip install bitarray
pip install Click
pip install pydub
```
