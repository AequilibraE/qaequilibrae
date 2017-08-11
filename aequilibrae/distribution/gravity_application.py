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
 Updated:    2017-08-11
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
from aequilibrae.distribution import Ipf, SyntheticGravityModel
from aequilibrae.matrix import AequilibraeMatrix, AequilibraEData
from time import clock

def main():
    pass


class GravityApplication:
    """"
    Model is an instance of SyntheticGravityModel class
    """

    def __init__(self, **kwargs):

        self.__required_parameters = ['max trip length']
        self.__required_model = ['function', 'parameters']

        self.parameters = kwargs.get('parameters', self.get_parameters('gravity'))

        self.rows = kwargs.get('rows')
        self.row_field = kwargs.get('row_field', None)

        self.columns = kwargs.get('columns')
        self.column_field = kwargs.get('column_field', None)

        self.impedance = kwargs.get('impedance')
        self.model = kwargs.get('model')

        self.output = None

    def apply(self):
        self.check_data()
        if self.error is None:
            t= clock()
            max_cost = self.parameters['max trip length']

            # We create the output
            self.output = self.impedance.copy()

            # We apply the function
            self.apply_function()

            # We zero those cells that have a trip length above the limit
            if max_cost > 0:
                a = (self.impedance.matrix_view[:,:,0] < max_cost).astype(int)
                self.output.matrix_view[:,:,0] = a * self.output.matrix_view[:,:,0]

            # We adjust the total of the self.output
            self.output.matrix_view[:,:,0] = self.output.matrix_view[:,:,0] * \
                                             (np.sum(self.rows) / np.sum(self.output.matrix_view[:,:,0]))

            # And adjust with a fratar
            ipf = Ipf(matrix=self.output, rows=self.rows, columns=self.columns,
                      column_field=self.column_field, row_field=self.row_field)

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
        self.report = ['  #####    GRAVITY APPLICATION    #####  ', '']
        self.check_parameters()

        if not isinstance(SyntheticGravityModel, self.model):
            self.error_free = False
            raise TypeError('Model is not an instance of SyntheticGravityModel')

        self.report.append('Model specification:')
        self.report.append('    Function: ' + self.model.function)
        if self.model.alpha is not None:
            self.report.append('    alpha: ' + str(self.model.alpha))

        if self.model.beta is not None:
            self.report.append('    beta: ' + str(self.model.beta))

        self.report.append('')

    # check dimensions
        # check data types
        if not isinstance(self.rows, AequilibraEData):
            raise TypeError('Row vector needs to be an instance of AequilibraEData')

        if not isinstance(self.columns, AequilibraEData):
            raise TypeError('Column vector needs to be an instance of AequilibraEData')

        if not isinstance(self.impedance, AequilibraeMatrix):
            raise TypeError('Seed matrix needs to be an instance of AequilibraEMatrix')

        # Check data dimensions
        if not np.array_equal(self.rows.index, self.columns.index):
            raise ValueError('Indices from row vector do not match those from column vector')

        if not np.array_equal(self.impedance.index, self.columns.index):
            raise ValueError('Indices from vectors do not match those from seed matrix')

        # Check if matrix was set for computation
        if self.impedance.matrix_view is None:
            raise ValueError('Matrix needs to be set for computation')
        else:
            if self.impedance.matrix_view.shape[2] > 1:
                raise ValueError("Matrix' computational view needs to be set for a single matrix core")

        # check balancing:
        sum_rows = np.sum(self.rows.data[self.row_field])
        sum_cols = np.sum(self.columns.data[self.column_field])
        if abs(sum_rows - sum_cols) > self.parameters['balancing tolerance']:
            raise ValueError( 'Vectors are not balanced')
        else:
            # guarantees that they are precisely balanced
            self.columns.data[self.column_field][:] = self.columns.data[self.column_field][:] * (
                sum_rows / sum_cols)

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
        for i in range(self.rows.entries):
            cost = self.impedance.matrix_view[i, :, 0]
            p = self.rows[i]
            a = self.columns[:]

            if self.model.function == "EXPO":
                self.output.matrix_view[i, :, 0] = np.exp(- self.model.beta * cost) * p * a[:]
            elif self.model.function == "POWER":
                self.output.matrix_view[i, :, 0] = np.nan_to_num(np.power(cost, - self.model.alpha) * p * a)[:]
            elif self.model.function == "GAMMA":
                self.output.matrix_view[i, :, 0] = np.nan_to_num(np.power(cost, self.model.alpha) * np.exp(- self.model.beta * cost) * p * a)[:]

        # Deals with infinite and NaNs
        infinite = np.isinf(self.output.matrix_view[i, :, 0]).astype(int)
        non_inf = np.ones_like(self.output.matrix_view[i, :, 0]) - infinite
        self.output.matrix_view[i, :, 0] = self.output.matrix_view[i, :, 0] * non_inf
        np.nan_to_num(self.output.matrix_view[i, :, 0])

if __name__ == '__main__':
    main()
