"""
-----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:      Synthetic gravity model class
 Purpose:    Implementing a class object to represent synthetic gravity models

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2017-08-11
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """


valid_functions = ['EXPO', 'GAMMA', 'POWER']
class SyntheticGravityModel:
    def __init__(self):
        self.function = None
        self.alpha = None
        self.beta = None

    def __setattr__(self, key, value):
        if value is None and key in ['function', 'alpha', 'beta']:
            self.__dict__[key] = value
        else:
            if key == 'function':
                self.alpha = None
                self.beta = None
                if value not in valid_functions:
                    raise ValueError('Function needs to be one of these: ' + ', '.join(valid_functions))
            else:
                if isinstance(value, float) or isinstance(value, int):
                    if key == 'alpha':
                        if self.__dict__.get("function") == 'EXPO':
                            raise ValueError('Exponential function does not have an alpha parameter')

                    if key == 'beta':
                        if self.function == 'POWER':
                            raise ValueError('Inverse power function does not have a beta parameter')
                else:
                    raise ValueError('Parameter needs to be numeric')

            self.__dict__[key] = value

    def load(self):
        pass