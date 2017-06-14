"""
-----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:      Synthetic gravity trip distribution model application
 Purpose:    Implementing the algorithms to apply trip distribution.
                  Implemented: Synthetic gravity with power, exponential and gamma functions
                  Still missing: 2nd stage: Friction factors

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-09-30
 Updated:    2016-10-03
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """
# The procedures implemented in this code are some of those suggested in
# Modelling Transport, 4th Edition
# Ortuzar and Willumsen, Wiley 2011
# The referred authors have no responsibility over this work, of course
import sys
sys.dont_write_bytecode = True

import numpy as np
import yaml
import os
from ipf import Ipf
from time import clock

def main():
    pass


class GravityApplication:
    """"
    Model specification is a dictionary of dictionaries:

        model = {function, parameters
                }
        where function is: 'EXPO', 'POWER' or 'GAMMA'

        and parameters are:  {alpha:..., beta:...}
    """
    def __init__(self, rows=None, columns=None, impedance=None, model=None, parameters=None):
        self.error = None
        self.error_free = True

        self.__required_parameters = ['max trip length']
        if parameters is None:
            parameters = self.get_parameters('gravity')

        self.__required_model = ['function', 'parameters']

        self.rows = rows
        self.columns = columns
        self.impedance = impedance
        self.parameters = parameters
        self.model = model
        self.output = None
        self.report = ['  #####    GRAVITY APPLICATION    #####  ', '']
        self.report.append('Model specification:')
        self.report.append('    ' + self.model['function'])
        for i in self.model['parameters'].keys():
            self.report.append('    ' + i + ': ' + str(self.model['parameters'][i]))
        self.report.append('')

    def apply(self):
        if self.error is None:
            t= clock()
            max_cost = self.parameters['max trip length']

            # We create the output
            self.output = np.zeros_like(self.impedance)

            # We apply the function
            self.apply_function()

            # We zero those cells that have a trip length above the limit
            if max_cost > 0:
                a = (self.impedance < max_cost).astype(int)
                self.output = a * self.output

            # We adjust the total of the self.output
            self.output = self.output * (np.sum(self.rows) / np.sum(self.output))

            # And adjust with a fratar
            ipf = Ipf(self.output, self.rows, self.columns)

            # We use the model application parameters in case they were provided
            # not the standard way of using this tool)
            for p in ipf.parameters:
                if p in self.parameters:
                    ipf.parameters[p] = self.parameters[p]

            # apply fratar
            ipf.fit()
            self.output = ipf.output

            q = ipf.report.pop(0)
            for q in ipf.report:
                self.report.append(q)

            self.report.append('')
            self.report.append('')

            self.report.append('Total of matrix: ' + "{:15,.4f}".format(np.sum(self.output)))
            self.report.append('Intrazonal flow: ' + "{:15,.4f}".format(np.trace(self.output)))
            self.report.append('Running time: ' +  str(round(clock()-t, 3)))

    def get_parameters(self, model):
        path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "."))
        with open(path + '/parameters.yml', 'r') as yml:
            path = yaml.safe_load(yml)
        return path['distribution'][model]

    def check_data(self):
        self.error = None
        self.check_parameters()

        # check dimensions
        if self.rows is None or self.columns is None or self.impedance is None:
            self.error = 'missing data'

        if self.error is None:
            # check vectors are indeed vectors and the matrix is two dimensional
            if len(self.rows.shape[:]) > 1:
                self.error = 'Rows is a 2+ dimensional array and not a vector'
            if len(self.columns.shape[:]) > 1:
                self.error = 'Columns is a 2+ dimensional array and not a vector'
            if len(self.impedance.shape[:]) != 2:
                self.error = 'Impedance matrix is not bi-dimensional'

            # check that vectors have the appropriate dimensions
            if self.rows.shape[0] != self.impedance.shape[0]:
                self.error = 'Dimensions for row vector and impedance matrix do not match'
            if self.columns.shape[0] != self.impedance.shape[1]:
                self.error = 'Dimensions for column vector and impedance matrix do not match'

            # check balancing:
            if abs(np.sum(self.rows) - np.sum(self.columns)) > self.parameters['balancing tolerance']:
                self.error = 'Vectors are not balanced'
            else:
                # guarantees that they are precisely balanced
                self.columns = self.columns * (np.sum(self.rows)/np.sum(self.columns))

        if self.error is not None:
            self.error_free = False

    def check_parameters(self):
        # Check if parameters are configured properly
        for p in self.__required_parameters:
            if p not in self.parameters:
                self.error = 'Parameters error. It needs to be a dictionary with the following keys: '
                for t in self.__required_parameters:
                    self.error = self.error + t + ', '
                break

        # Check if model function and parameters are provided properly
        for p in self.__required_model:
            if p not in self.model:
                self.error = 'Model specification not provided correctly. It needs ' \
                             'to be a dictionary with the following keys: '
                for t in self.__required_model:
                    self.error = self.error + t + ', '
                break

    def apply_function(self):
        function = self.model['function']
        param = self.model['parameters']

        if function.upper() == "EXPO":
            beta = param['beta']
        elif function.upper() == "POWER":
            alpha = param['alpha']
        elif function.upper() == "GAMMA":
            beta = param['beta']
            alpha = param['alpha']
        else:
            self.error = 'Model specification error. Function not defined'

        for i in range(self.rows.shape[0]):
            cost = self.impedance[i, :]
            p = self.rows[i]
            a = self.columns[:]

            if function.upper() == "EXPO":
                self.output[i, :] = np.exp(-beta * cost) * p * a
            elif function.upper() == "POWER":
                self.output[i, :] = np.nan_to_num(np.power(cost, -alpha) * p * a)
            elif function.upper() == "GAMMA":
                self.output[i, :] = np.nan_to_num(np.power(cost, alpha) * np.exp(-beta * cost) * p * a)

        # Deals with infinite and NaNs
        infinite = np.isinf(self.output).astype(int)
        non_inf = np.ones_like(self.output) - infinite
        self.output = self.output * non_inf
        np.nan_to_num(self.output)

if __name__ == '__main__':
    main()
