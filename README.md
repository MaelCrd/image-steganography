# steganography-images

## The purpose of this project is to provide a way to hide data in images

The project is based on the [Steganography](https://en.wikipedia.org/wiki/Steganography) technique  
The project is written in Python and uses the [Pillow](https://github.com/python-pillow/Pillow) and [Numpy](https://numpy.org/) library.

### Informations about the project

- Maximal size of the data to hide: 2^32 bits (0.536871 Go)
- Maximum count of bits per pixel: 24 (3*8)


file composition:  
|             data               |  (extension)  |  extension bit  |  encoding bit  | size |  
|:------------------------------:|:-------------:|:---------------:|:--------------:|:----:|
|:------------------------------:|:-------------:|:---------------:|:--------------:|:----:|
