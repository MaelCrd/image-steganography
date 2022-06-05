# main.py
import sys
from PIL import Image
import numpy as np
import argparse


# Constants
MAX_EXTENSION_CHARS = 6                       # Maximum number of characters in the extension
DEFAULT_EXTENSION_BITS_PER_CHAR = 7           # 7 bits per char
MAX_EXTENSION_BITS = MAX_EXTENSION_CHARS*7    # 6 chars * 7 bits per char
DEFAULT_BITS_ENCODING = 1                     # 2 bits per color channel
MAX_BITS_ENCODING = 7                         # Maximum number of bits per color channel


# Verbose print
v_print = None


# Round up to the nearest integer
def round_up(n):
  return int(n) + bool(n%1)


# Convert a bytes string to a bitstring
def bytes_to_bitstring(b):
  return "{:08b}".format(int(b.hex(),16))


# Convert a bitstring to a bytes string
def bitstring_to_bytes(s):
  return int(s, 2).to_bytes((len(s) + 7) // 8, byteorder='big')


# Convert an integer to a bitstring
def int_to_bitstring(i):
  return format(i, 'b')


# Convert an integer to a bitstring of a given length
def int_to_bitstring(i, n_bits):
  return str(format(i, 'b').zfill(n_bits))[-n_bits:]


# Convert a bitstring to an integer
def bitstring_to_int(s):
  return int(s, 2)


# Convert a string to a bitstring
def string_to_bitstring(s):
  return ''.join(format(ord(i),'b') for i in s)


# Convert a string to a bitstring given a number of bits per character
def string_to_bitstring(s, bits_per_char):
  return ''.join(format(ord(i),'b').zfill(bits_per_char) for i in s)


# Convert a bitstring to a string given a number of bits per character
def bitstring_to_string(bitstring, bits_per_char):
  return "".join([chr(int(b, 2)) for b in slice_string(bitstring, bits_per_char)])


# Slice a string into a list of strings of a given length
def slice_string(s, every):
  return [s[int(every*i):int(every*i+every)] for i in range(int(len(s)/every))]


# Cut a bitstring to a given length keeping the last bits 
def n_bits_cut_bitstring(s, n_bits, length):
  if length is None:
    return s
  else:
    index = (length-length%n_bits)
    result = s[:index]
    if (length%n_bits) != 0:
      result += (s[index:index+n_bits])[-(length%n_bits):]
    return result


# Return the extension of a file
def get_file_extension(filename):
  filename_parts = filename.split('.')
  if len(filename_parts) > 1:
    return filename_parts[-1]
  else:
    return ""


# Remove null characters from a string
def remove_null_characters(s: str):
  return s.replace(chr(0), "")


# Encode bits in an integer
def encode_value(x, y, n):
  return x - x%(2**n) + y%(2**n)


# Encode a color given a bitstring
def encode_color(base_color, binary_string_part):
  return encode_value(base_color, bitstring_to_int(binary_string_part), len(binary_string_part))


# Decode a color given a number of bits per color channel
def decode_color(color, n_bits):
  return int_to_bitstring(color, n_bits)


# Encode a pixel given a bitstring and a number of bits per color channel
def encode_pixel(pixel, binary_string, index, n_bits):
  new_pixel = list(pixel)
  for i in range(3):
    if index < len(binary_string):
      new_pixel[i] = encode_color(new_pixel[i], binary_string[index:index+n_bits])
      index += n_bits
    else:
      break
  return tuple(new_pixel), index


# Decode a pixel given a number of bits per color channel
def decode_pixel(pixel, n_bits):
  return "".join([decode_color(pixel[i], n_bits) for i in range(3)])
  

# Return the total number of pixels in an image
def get_image_total_pixels(image_size):
  return image_size[0] * image_size[1]


# Return the total number of bits that can be encoded in an image
def get_image_max_bits(image_size):
  return get_image_total_pixels(image_size) * 3 * MAX_BITS_ENCODING


# Return the number of bits that can be encoded in an image given the number of bits per color channel
def get_image_total_bits(image_size, n_bits):
  return get_image_total_pixels(image_size) * 3 * n_bits


# Return the number of bits used to store the encoded data size
def get_image_size_bits(image_size):
  return round_up(np.log(get_image_max_bits(image_size) - MAX_EXTENSION_BITS - 4) / np.log(2.035)) + 1


# Return the number of pixels used to store the encoded data size in an image given the number of bits per color channel
def get_image_size_pixels(image_size, n_bits):
  return round_up(get_image_size_bits(image_size) / (3 * n_bits))


# Return the number of pixels used to store the encoded file extension in an image given the number of bits per color channel
def get_extension_pixels_count(n_bits):
  return round_up(MAX_EXTENSION_BITS / (3 * n_bits))


# Return the number of pixels used to store the encoded data in an image given the number of bits per color channel
def get_data_pixels_count(data_bits_size, n_bits):
  return round_up(data_bits_size / (3 * n_bits))


# Return the pixel number where is stored the encoding bit
def get_start_pixel_encoding_bit_index(image_size):
  return get_image_total_pixels(image_size) - 1


# Return the number of the first pixel where is stored the size of the encoded data
def get_start_pixel_size_index(image_size, image_size_pixels):
  return get_image_total_pixels(image_size) - image_size_pixels - 1


# Return the pixel number where is stored the has_extension bit
def get_start_pixel_extension_index(image_size, image_size_pixels):
  return get_start_pixel_size_index(image_size, image_size_pixels) - 1


# Hide a bitstring in an image given the number of bits per color channel and the first pixel
def hide_data_into_image(to_hide_binary_string, output_image, n_bits, start_pixel_index=0):
  index = 0
  start_x = start_pixel_index % output_image.size[0]
  for x in range(start_x, output_image.size[0]):
    for y in range(output_image.size[1]):
      pixel_number = x + y * output_image.size[0]
      if pixel_number >= start_pixel_index:
        pixel = output_image.getpixel((x,y))
        pixel, index = encode_pixel(pixel, to_hide_binary_string, index, n_bits)
        output_image.putpixel((x,y), pixel)
      if index >= len(to_hide_binary_string):
        return output_image
  return output_image


# Decode a bitstring from an image given the number of bits per color channel, the first pixel, the number of pixels and the number of bits to have in the bitstring
def decode_data_from_image(input_image, n_bits, start_pixel_index, data_pixel_count=None, total_bits=None):
  if data_pixel_count is None:
    data_pixel_count = get_image_total_pixels(input_image.size)
  pixel_count = 0
  output_binary_string = ""
  start_x = start_pixel_index % input_image.size[0]
  for x in range(start_x, input_image.size[0]):
    for y in range(input_image.size[1]):
      pixel_number = x + y * input_image.size[0]
      if pixel_number >= start_pixel_index:
        pixel = input_image.getpixel((x,y))
        output_binary_string += decode_pixel(pixel, n_bits)
        pixel_count += 1
      if pixel_count >= data_pixel_count:
        return n_bits_cut_bitstring(output_binary_string, n_bits, total_bits)
  return n_bits_cut_bitstring(output_binary_string, n_bits, total_bits)


# Hide the size of the encoded data in an image
def hide_size_into_image(to_hide_binary_string_length, output_image, start_pixel_index, image_size_bits, n_bits):
  v_print("Hiding size of data to hide...")
  size_binary_string = int_to_bitstring(to_hide_binary_string_length, image_size_bits)
  return hide_data_into_image(size_binary_string, output_image, n_bits, start_pixel_index=start_pixel_index)


# Hide the has_extension bit of the encoded data file in an image
def hide_extension_bit_into_image(file_has_extension_bit, output_image, start_pixel_index):
  v_print("Hiding extension bit...")
  return hide_data_into_image(file_has_extension_bit, output_image, 1, start_pixel_index=start_pixel_index)


# Hide the extension of the encoded data file in an image
def hide_extension_into_image(to_hide_filename, output_image, start_pixel_index, image_extension_pixels_count, n_bits):
  file_has_extension_bit = ""
  if get_file_extension(to_hide_filename) != "":
    v_print(f"Hiding file extension (.)\"{get_file_extension(to_hide_filename)}\"...")
    file_has_extension_bit = "1"
    extension_binary_string = string_to_bitstring(get_file_extension(to_hide_filename), DEFAULT_EXTENSION_BITS_PER_CHAR).zfill(MAX_EXTENSION_BITS)
    output_image = hide_data_into_image(extension_binary_string, output_image, n_bits, start_pixel_index=start_pixel_index - image_extension_pixels_count)
  else:
    v_print("No file extension to hide.")
    file_has_extension_bit = "0"
  return hide_extension_bit_into_image(file_has_extension_bit, output_image, start_pixel_index)


# Hide the encoding bit of the encoded data in an image
def hide_encoding_bit_into_image(output_image, start_pixel_index, n_bits):
  v_print("Hiding encoding bit...")
  encoding_bit_binary_string = int_to_bitstring(n_bits, 3)
  v_print("Encoding bit binary string:", encoding_bit_binary_string)
  return hide_data_into_image(encoding_bit_binary_string, output_image, 1, start_pixel_index=start_pixel_index)


# Hide a file into an image
def encode_file(to_hide_filename, input_filename, output_filename, n_bits):
  # Check if bits encoding is forced
  force_n_bits = n_bits is not None
  if not force_n_bits:
    n_bits = DEFAULT_BITS_ENCODING
  
  # Open the input image and the file to hide
  input_image = Image.open(input_filename)
  to_hide_file = open(to_hide_filename, 'rb')

  # Get the bitstring of the content from the file to hide
  to_hide_binary_string = bytes_to_bitstring(to_hide_file.read())

  # Close the file to hide
  to_hide_file.close()

  # Create the output image as a copy of the input image
  output_image = input_image.copy()

  # Get the total number of pixels of the image and the number of bits used to store the size of the data to hide
  image_total_pixels = get_image_total_pixels(output_image.size)
  image_size_bits = get_image_size_bits(output_image.size)

  while True:
    # Get the number of bits that can be used in the image
    image_total_bits = get_image_total_bits(output_image.size, n_bits)

    # Print some information when verbose is enabled
    v_print(len(to_hide_binary_string), "bits to hide")
    v_print(image_total_pixels, "pixels :", image_total_bits, f"bits available (minus {image_size_bits + MAX_EXTENSION_BITS + 5} used to store size and extension)")
    v_print('Bits encoding:', n_bits, 'bits per color channel') 

    if len(to_hide_binary_string) + image_size_bits + MAX_EXTENSION_BITS < image_total_bits:
      break
    
    # Increase the number of bits used to encode the data
    n_bits += 1

    # Abort if the data to hide is too big to be encoded in the image or if the number of bits per color channel is too high
    if force_n_bits or n_bits > MAX_BITS_ENCODING:
      print("Error: image is too small to hide data." + (" Try to increase the number of bits per color channel." if force_n_bits and n_bits-1 < MAX_BITS_ENCODING else ""))
      sys.exit(1)  
  
  # Get the number of pixels used to store the size and extension of the data to hide
  image_size_pixels = get_image_size_pixels(output_image.size, n_bits)
  image_extension_pixels_count = get_extension_pixels_count(n_bits)

  # Write the file extension into the image
  start_pixel_index = get_start_pixel_extension_index(output_image.size, image_size_pixels)
  output_image = hide_extension_into_image(to_hide_filename, output_image, start_pixel_index, image_extension_pixels_count, n_bits)

  # Write the size of the data to hide into the image
  start_pixel_index = get_start_pixel_size_index(output_image.size, image_size_pixels)
  output_image = hide_size_into_image(len(to_hide_binary_string), output_image, start_pixel_index, image_size_bits, n_bits)

  # Write the encoding bit into the image
  start_pixel_index = get_start_pixel_encoding_bit_index(output_image.size)
  output_image = hide_encoding_bit_into_image(output_image, start_pixel_index, n_bits)
  
  # Write the data to hide into the image
  v_print("Hiding data...")
  output_image = hide_data_into_image(to_hide_binary_string, output_image, n_bits)

  # Save the output image
  output_image.save(output_filename, optimize=False, quality=100)

  # Close opened images
  input_image.close()
  output_image.close()

  # Print some information
  v_print("Done.")
  print(f"Encoded file saved to \"{output_filename}\"")
  

# Decode a file from an image
def decode_image(input_filename, output_filename):
  v_print("Decoding...")

  # Open the input image
  input_image = Image.open(input_filename)

  # Read the encoding bit from the image
  start_pixel_index = get_start_pixel_encoding_bit_index(input_image.size)
  encoding_bit_binary_string = decode_data_from_image(input_image, 1, start_pixel_index, data_pixel_count=1)
  
  # Get the number of bits per color channel from the encoding bit
  n_bits = int(encoding_bit_binary_string, 2)
  v_print(f"Encoding bits: {n_bits}")

  # Get the number of pixels/bits used to store the size/extension of the data to hide
  image_size_pixels = get_image_size_pixels(input_image.size, n_bits)
  image_size_bits = get_image_size_bits(input_image.size)
  image_extension_pixels_count = get_extension_pixels_count(n_bits)

  # Read the size of the data to decode from the image
  start_pixel_index = get_start_pixel_size_index(input_image.size, image_size_pixels)
  data_size_bits_bitstring = decode_data_from_image(input_image, n_bits, start_pixel_index, data_pixel_count=image_size_pixels, total_bits=image_size_bits)
  data_bits_size = bitstring_to_int(data_size_bits_bitstring)
  v_print(f"Data size: {data_bits_size} bits")

  # Read the extension bit from the image
  start_pixel_index = get_start_pixel_extension_index(input_image.size, image_size_pixels)
  extension_bit_binary_string = decode_data_from_image(input_image, 1, start_pixel_index, data_pixel_count=1, total_bits=1)
  has_extension = extension_bit_binary_string == "1"
  v_print(f"Has extension: {has_extension}")

  # Read the extension from the image if it exists
  if has_extension:
    start_pixel_index = get_start_pixel_extension_index(input_image.size, image_size_pixels) - image_extension_pixels_count
    extension_binary_string = decode_data_from_image(input_image, n_bits, start_pixel_index, data_pixel_count=image_extension_pixels_count, total_bits=MAX_EXTENSION_BITS)
    extension_string = remove_null_characters(bitstring_to_string(extension_binary_string, DEFAULT_EXTENSION_BITS_PER_CHAR))
    v_print(f"File extension: (.)\"{extension_string}\"")
  
  # Read the data encoded in the image
  data_binary_string = decode_data_from_image(input_image, n_bits, 0, data_pixel_count=get_data_pixels_count(data_bits_size, n_bits), total_bits=data_bits_size)
  data_bytes = bitstring_to_bytes(data_binary_string)
  v_print(f"{len(data_binary_string)} bits and {len(data_bytes)} bytes decoded")

  # Save the decoded data into a file
  decoded_filename = output_filename if output_filename is not None else "decoded"
  if has_extension:
    decoded_filename += "." + extension_string
  with open(decoded_filename, "wb") as f:
    f.write(data_bytes)

  # Print some information
  print(f"Decoded file saved to \"{decoded_filename}\"")
  v_print("Done.")


# Main
if __name__ == "__main__":
  # Create argument parser
  parser = argparse.ArgumentParser()

  # Arguments for Argument Parser
  parser.add_argument('-e', '--encode', nargs=3, metavar=('file', 'source', 'destination'), help="Encode file into image")
  parser.add_argument('-d', '--decode', nargs=1, metavar=('file'), help="Decode image into file")
  parser.add_argument('-b', '--bits', type=int, metavar=('N'), help="Force number of bits changed per color channel", default=None)
  parser.add_argument('-v', '--verbose', action='store_true', help="Verbose output")
  parser.add_argument('-dd', '--decode-destination', type=str, metavar=('file'), help="Destination file (without extension) for decoded file", default=None)
  parser.add_argument('-li', '--large-image', action='store_true', help="Use large image (0.2GB+) (default: False)", default=False)

  # Parse arguments from command line
  args = parser.parse_args()

  # Check if bits argument is valid
  if args.bits is not None:
    if args.bits < 1 or args.bits > MAX_BITS_ENCODING:
      raise argparse.ArgumentTypeError("Bits must be between 1 and 7")

  # Set verbose
  v_print = print if args.verbose else lambda *a, **k: None

  # Remove max image pixels limit if large image is set to True
  if args.large_image:
    Image.MAX_IMAGE_PIXELS = None

  # If encode arguments are given
  if args.encode is not None:
    encode_file(args.encode[0], args.encode[1], args.encode[2], args.bits)
  
  # If decode arguments are given
  if args.decode is not None:
    decode_image(args.decode[0], args.decode_destination)
  
  # If neither encode nor decode arguments are given
  if args.encode is None and args.decode is None:
    parser.print_help()
