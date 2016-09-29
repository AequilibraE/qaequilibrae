# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------
# Name:       Iterative proportional fitting
# Purpose:    Implement Iterative proportinal fitting
#
# Author:      Pedro Camargo
# Website:    www.AequilibraE.com
# Repository:  
#
# Created:     29/09/2016
# Copyright:   (c) AequilibraE authors
# Licence:     See LICENSE.TXT
# -------------------------------------------------------------------------------

import numpy as np
import os
import yaml
from time import clock

class Ipf:
    def __init__(self, seed=None, rows=None, columns=None, parameters = None):
        if parameters is None:
            parameters = self.get_parameters('ipf')

        self.seed = seed
        self.rows = rows
        self.columns = columns
        self.parameters = parameters
        self.output = None
        self.error = None
        self.__required_parameters=['convergence level', 'max iteractions', 'balancing tolerance']
        self.error_free = True
        self.report = ['  #####    IPF computation    #####  ', '']

    def check_data(self):
        self.error = None
        self.check_parameters()

        # check dimensions
        if self.rows is None or self.columns is None or self.seed is None or self.parameters is None:
            self.error = 'missing data'

        if self.error is None:
            # check vectors are indeed vectors and the matrix is two dimensional
            if len(self.rows.shape[:]) > 1:
                self.error = 'Rows is a 2+ dimensional array and not a vector'
            if len(self.columns.shape[:]) > 1:
                self.error = 'Columns is a 2+ dimensional array and not a vector'
            if len(self.seed.shape[:]) != 2:
                self.error = 'Seed matrix is not bi-dimensional'

            # check that vectors have the appropriate dimensions
            if self.rows.shape[0] != self.seed.shape[0]:
                self.error = 'Dimensions for row vector and seed matrix do not match'
            if self.columns.shape[0] != self.seed.shape[1]:
                self.error = 'Dimensions for column vector and seed matrix do not match'

            # check balancing:
            if abs(np.sum(self.rows) - np.sum(self.columns)) > self.parameters['balancing tolerance']:
                self.error = 'Vectors are not balanced'
            else:
                # guarantees that they are precisely balanced
                self.columns = self.columns* (np.sum(self.rows)/np.sum(self.columns))

        if self.error is not None:
            print self.error
            self.error_free = False

    def check_parameters(self):
        for i in self.__required_parameters:
            if i not in  self.parameters:
                self.error = 'Parameter list not complete'

    def fit(self):
        t = clock()
        self.check_data()
        if self.error_free:
            max_iter =  self.parameters['max iteractions']
            conv_criteria = self.parameters['convergence level']
            self.output = np.copy(self.seed)

            # Reporting
            self.report.append('Target convergence criteria: ' + str(conv_criteria))
            self.report.append('Maximum iterations: ' + str(max_iter))
            self.report.append('')
            self.report.append('Rows:' + str(self.rows.shape[0]))
            self.report.append('Columns: ' + str(self.columns.shape[0]))
            self.report.append('Total of seed matrix: ' + str("{:28,.4f}".format(np.sum(self.seed))))
            self.report.append('Total of target vectors: ' + str("{:25,.4f}".format(np.sum(self.rows))))
            self.report.append('')
            self.report.append('Iteration,   Convergence')
            gap = conv_criteria + 1

            iter = 0
            while gap > conv_criteria and iter < max_iter:
                iter += 1

                # computes factors for rows
                marg_rows = self.tot_rows(self.output)
                row_factor = self.factor(marg_rows, self.rows)
                # applies factor
                self.output = np.transpose(np.transpose(self.output) * np.transpose(row_factor))

                # computes factors for columns
                marg_cols = self.tot_columns(self.output)
                column_factor = self.factor(marg_cols, self.columns)

                # applies factor
                self.output = self.output * column_factor

                # increments iterarions and computes errors
                gap = max(abs(1 - np.min(row_factor)), abs(np.max(row_factor) - 1), abs(1 - np.min(column_factor)),
                            abs(np.max(column_factor) - 1))
                self.report.append(str(iter) + '   ,   ' + str("{:4,.10f}".format(np.sum(gap))))
            self.report.append('')
            self.report.append('Running time: ' + str("{:4,.3f}".format(clock()-t)) + 's')
    def tot_rows(self, matrix):
        return np.sum(matrix, axis=1)

    def tot_columns(self, matrix):
        return np.sum(matrix, axis=0)

    def factor(self, marginals, targets):
        f = np.divide(targets, marginals)  # We compute the factors
        f[f == np.NINF] = 1  # And treat the errors, with the infinites first
        f = f + 1  # and the NaN second
        f = np.nan_to_num(f)  # The sequence of operations is just a resort to
        f[f == 0] = 2  # use at most numpy functions as possible instead of pure Python
        f = f - 1
        return f

    def get_parameters(self, model):
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        with open(path + '/parameters.yml', 'r') as yml:
            path = yaml.safe_load(yml)
        return path['distribution'][model]

###For testing
rows = np.random.rand(1000)*10000
# columns = np.random.rand(1000)*10000
# columns = columns * (np.sum(rows)/np.sum(columns))
# mat = np.random.rand(1000,1000)
#
# ipf = Ipf(mat, rows, columns)
# ipf.fit()
# for i in ipf.report:
#     print i