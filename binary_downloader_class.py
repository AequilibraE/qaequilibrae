

import os
import urllib
my_system_binary_path = 'https://github.com/AequilibraE/AequilibraE/releases/download/V.0.3.3.1/AoN_linux64.so'
local_path = os.path.dirname(os.path.abspath(__file__)) + '/AoN.so'
urllib.urlretrieve(my_system_binary_path, local_path)