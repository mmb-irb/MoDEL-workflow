# Auxiliar generic functions and classes used along the workflow

from model_workflow.utils.constants import RESIDUE_NAME_LETTERS, YELLOW_HEADER, COLOR_END

from os import rename, listdir
from os.path import isfile
import sys
import json
import yaml
from glob import glob
from typing import Optional, List, Generator
from struct import pack

# Check if a module has been imported
def is_imported (module_name : str) -> bool:
    return module_name in sys.modules

# Set custom exception which is not to print traceback
# They are used when the problem is not in our code
class QuietException (Exception):
    pass

# Set a custom quite exception for when user input is wrong
class InputError (QuietException):
    pass

# Set a custom quite exception for when MD data has not passed a quality check test
class TestFailure (QuietException):
    pass

# Set a custom quite exception for when the problem comes from a third party dependency
class ToolError (QuietException):
    pass

# Set a custom quite exception for when the problem comes from a remote service
class RemoteServiceError (QuietException):
    pass

# Set a custom exception handler where our input error exception has a quiet behaviour
def custom_excepthook (exception_class, message, traceback):
    # Quite behaviour if it is our input error exception
    if QuietException in exception_class.__bases__:
        print('{0}: {1}'.format(exception_class.__name__, message))  # Only print Error Type and Message
        return
    # Default behaviour otherwise
    sys.__excepthook__(exception_class, message, traceback)
sys.excepthook = custom_excepthook

# Set a function to get the next letter from an input letter in alphabetic order
# Return None if we run out of letters
letters = { 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z' }
def get_new_letter(current_letters : set) -> Optional[str]:
    return next((letter for letter in letters if letter not in current_letters), None)

# Given a residue name, return its single letter
def residue_name_to_letter (residue_name : str) -> str:
    return RESIDUE_NAME_LETTERS.get(residue_name, 'X')

# Set a JSON loader with additional logic to better handle problems
def load_json (filepath : str):
    try:
        with open(filepath, 'r') as file:
            content = json.load(file)
        return content
    except:
        raise Exception('Something went wrong when loading JSON file ' + filepath)
    
# Set a JSON saver with additional logic to better handle problems
def save_json (content, filepath : str, indent : Optional[int] = None):
    try:
        with open(filepath, 'w') as file:
            json.dump(content, file, indent=indent)
    except:
        # Rename the JSON file since it will be half written thus giving problems when loaded
        rename(filepath, filepath + '.wrong')
        raise Exception('Something went wrong when saving JSON file ' + filepath)

# Set a YAML loader with additional logic to better handle problems
# DANI: Por algún motivo yaml.load también funciona con archivos en formato JSON
def load_yaml (filepath : str):
    try:
        with open(filepath, 'r') as file:
            content = yaml.load(file, Loader=yaml.CLoader)
        return content
    except Exception as error:
        warn(str(error).replace('\n', ' '))
        raise InputError('Something went wrong when loading YAML file ' + filepath)

# Set a YAML saver with additional logic to better handle problems
def save_yaml (content, filepath : str):
    with open(filepath, 'w') as file:
        yaml.dump(content, file)

# Set a few constants to erase previou logs in the terminal
CURSOR_UP_ONE = '\x1b[1A'
ERASE_LINE = '\x1b[2K'
ERASE_PREVIOUS_LINES = CURSOR_UP_ONE + ERASE_LINE + CURSOR_UP_ONE

# Set a function to remove previous line
def delete_previous_log ():
    print(ERASE_PREVIOUS_LINES)

# Set a function to reprint in the same line
def reprint (text : str):
    delete_previous_log()
    print(text)

# Set a function to print a messahe with a colored warning header
def warn (message : str):
    print(YELLOW_HEADER + '⚠  WARNING: ' + COLOR_END + message)

# Round a number to hundredths
def round_to_hundredths (number : float) -> float:
    return round(number * 100) / 100

# Round a number to hundredths
def round_to_thousandths (number : float) -> float:
    return round(number * 1000) / 1000

# Given a list with numbers,  create a string where number in a row are represented rangedly
# e.g. [1, 3, 5, 6, 7, 8] => "1, 3, 5-8"
def ranger (numbers : List[int]) -> str:
    # Remove duplicates and sort numbers
    sorted_numbers = sorted(list(set(numbers)))
    # Get the number of numbers in the list
    number_count = len(sorted_numbers)
    # If there is only one number then finish here
    if number_count == 1:
        return str(sorted_numbers[0])
    # Start the parsing otherwise
    ranged = ''
    last_number = -1
    # Iterate numbers
    for i, number in enumerate(sorted_numbers):
        # Skip this number if it was already included in a previous serie
        if i <= last_number: continue
        # Add current number to the ranged string
        ranged += ',' + str(number)
        # Now iterate numbers after the current number
        next_index = i+1
        for j, next_number in enumerate(sorted_numbers[next_index:], next_index):
            # Set the length of the serie
            length = j - i
            # End of the serie
            if next_number - number != length:
                # The length here is the length which broke the serie
                # i.e. if the length here is 2 the actual serie length is 1
                serie_length = length - 1
                if serie_length > 1:
                    last_serie_number = j - 1
                    previous_number = sorted_numbers[last_serie_number]
                    ranged += '-' + str(previous_number)
                    last_number = last_serie_number
                break
            # End of the selection
            if j == number_count - 1:
                if length > 1:
                    ranged += '-' + str(next_number)
                    last_number = j
    # Remove the first coma before returning the ranged string
    return ranged[1:]

# Set a special iteration system
# Return one value of the array and a new array with all other values for each value
def otherwise (values : list) -> Generator[tuple, None, None]:
    for v, value in enumerate(values):
        others = values[0:v] + values[v+1:]
        yield value, others

# List files in a directory
def list_files (directory : str) -> List[str]:
    return [f for f in listdir(directory) if isfile(f'{directory}/{f}')]

# Set a function to check if a string has patterns to be parsed by a glob function
# Note that this is not trivial, but this function should be good enough for our case
# https://stackoverflow.com/questions/42283009/check-if-string-is-a-glob-pattern
GLOB_CHARACTERS = ['*', '?', '[']
def is_glob (path : str) -> bool:
    # Find unescaped glob characters
    for c, character in enumerate(path):
        if character not in GLOB_CHARACTERS:
            continue
        if c == 0:
            return True
        previous_characters = path[c-1]
        if previous_characters != '\\':
            return True
    return False

# Parse a glob path into one or several results
# If the path has no glob characters then return it as it is
# Otherwise make sure
def parse_glob (path : str) -> List[str]:
    # If there is no glob pattern then just return the string as is
    if not is_glob(path):
        return [ path ]
    # If there is glob pattern then parse it
    parsed_filepaths = glob(path)
    return parsed_filepaths

# Supported byte sizes
SUPPORTED_BYTE_SIZES = {
    2: 'e',
    4: 'f',
    8: 'd'
}

# Data is a list of numeric values
# Bit size is the number of bits for each value in data to be occupied
def store_binary_data (data : List[float], byte_size : int, filepath : str):
    # Check bit size to make sense
    letter = SUPPORTED_BYTE_SIZES.get(byte_size, None)
    if not letter:
        raise ValueError(f'Not supported byte size {byte_size}, please select one of these: {", ".join(SUPPORTED_BYTE_SIZES.keys())}')
    # Set the binary format
    # '<' stands for little endian
    byte_flag = f'<{letter}'
    # Start writting the output file
    with open(filepath, 'wb') as file:
        # Iterate over data list values
        for value in data:
            value = float(value)
            file.write(pack(byte_flag, value))