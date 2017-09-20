import os

a = open(os.path.join(os.path.dirname(__file__), 'paths/parameters.pxi'), 'r')
for i in a.readlines():
    if 'VERSION' in i:
        version = i[11:]
    if 'MINOR_VRSN' in i:
        minor_version = i[14:]
    if 'release_name' in i:
        release_name = i[17:-1]

release_version = str(version) + '.' + str(minor_version)
"""TODO: Come up with a name for this version (and a naming convention) """
