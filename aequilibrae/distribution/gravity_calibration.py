"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Gravity model calibration
 Purpose:    Implement a procedure to calibrate gravity models

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    22/10/2016
 Updated:    22/10/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
"""

# The procedures implemented in this code are some of those suggested in
# Modelling Transport, 4th Edition
# Ortuzar and Willumsen, Wiley 2011

# The referred authors have no responsability over this work, of course

import sys, os
from time import clock, strftime, gmtime
from gravity_application import GravityApplication
import numpy as np
import sys
import yaml

class GravityCalibration:
    """"
        where function is: 'EXPO' or 'POWER'. 'GAMMA' and 'FRICTION FACTORS' to be implemented at a later time
        parameters are: 'max trip length'
        """
    def __init__(self, matrix=None, cost_matrix=None, function=None, parameters=None):

        self.__required_parameters = ['max trip length', 'max iterations', 'max error']
        if parameters is None:
            parameters = self.get_parameters('gravity')

        self.matrix = matrix
        self.result_matrix = None
        self.cost_matrix = cost_matrix
        self.function = function.upper()
        self.parameters = parameters

        self.error = None
        self.gravity = None
        self.report = ['  #####    GRAVITY CALIBRATION    #####  ', '']

        self.itera = 0
        self.max_iter = None
        self.max_error = None
        self.conv = np.inf
        self.report.append('')
        self.report.append('Functional form: ' + self.function)
        self.model = {'function': function}

    def calibrate(self):
        t = clock()
        # initialize auxiliary variables
        b0, b1, c0, c1 = None, None, None, None
        max_cost = self.parameters['max trip length']
        self.max_iter = self.parameters['max iterations']
        self.max_error = self.parameters['max error']

        # Check the inputs
        self.check_inputs()
        if self.error is None:
            if self.function in ["EXPO", "POWER"]:

                def assemble_model(b1):
                    # NEED TO SET PARAMETERS #
                    if self.function == "EXPO":
                        self.model['parameters'] = {'beta': float(b1)}
                    elif self.function == "POWER":
                        self.model['parameters'] = {'alpha': float(b1)}

                # filtering for all costs over limit
                a = (self.matrix < max_cost).astype(int)

                #weighted average cost
                self.report.append('Iteration: 1')
                cstar = np.sum(self.matrix * self.cost_matrix * a) / np.sum(self.matrix * a)
                b0 = 1 / cstar

                assemble_model(b0)
                c0 = self.apply_gravity()
                for i in self.gravity.report:
                    self.report.append('       ' + i)
                self.report.append('')
                self.report.append('')

                bm1 = b0
                bm = b0 * c0 / cstar

                self.report.append('Iteration: 2')
                assemble_model(bm)
                cm = self.apply_gravity()
                for i in self.gravity.report:
                    self.report.append('       ' + i)
                self.report.append('Error: ' +  "{:.2E}".format(np.sum(abs((bm / bm1) - 1))))
                self.report.append('')
                cm1 = c0

            # While the max iterations has not been reached and the error is still too large
            self.itera = 2
            while self.itera < self.max_iter and self.conv > self.max_error:
                self.report.append('Iteration: ' + str(self.itera + 1))
                aux = bm
                bm = ((cstar - cm1) * bm - (cstar - cm) * bm) / (cm - cm1)
                bm1 = aux
                cm1 = cm

                assemble_model(bm1)
                cm = self.apply_gravity()

                for i in self.gravity.report:
                    self.report.append('       ' + i)
                self.report.append('Error: ' + "{:.2E}".format(np.sum(abs((bm / bm1) - 1))))
                self.report.append('')

                # compute convergence criteria
                print bm
                print bm1
                self.conv = abs((bm / bm1) - 1)
                self.itera += 1

            if self.itera == self.max_iter:
                self.report.append("DID NOT CONVERGE. Stopped in  " + str(self.itera) + "  with a global error of " + str(self.conv))
            else:
                self.report.append("Converged in " + str(self.itera) + "  iterations to a global error of " + str(self.conv))
            s = clock() - t
            m, s1 = divmod(s, 60)
            s -= m * 60
            h, m = divmod(m, 60)
            t =  "%d:%02d:%2.4f" % (h, m, s)

            self.report.append('Running time: ' + t)
        else:
            self.report.append(self.error)

    def check_inputs(self):
        if self.matrix.shape[:] != self.cost_matrix.shape[:]:
            self.error = "Observed matrix and cost matrix do not have the same dimensions"

        elif not np.sum(self.matrix):
            self.error = 'Observed matrix has no flows'

        elif not np.sum(self.cost_matrix):
            self.error = 'Cost matrix is all zero'

        elif not np.sum(self.cost_matrix * self.matrix):
            self.error = 'All cells with positive flows have zero costs'

        elif np.min(self.cost_matrix) < 0:
            self.error = 'Cost matrix has negative values'

        elif np.min(self.matrix) < 0:
            self.error = 'Observed matrix has negative values'

    def apply_gravity(self):
        self.gravity = GravityApplication(rows=np.sum(self.matrix, axis=0), columns=np.sum(self.matrix, axis=1),
                                          impedance=self.cost_matrix, model=self.model, parameters=self.parameters)
        self.gravity.apply()
        self.result_matrix = self.gravity.output
        return np.sum(self.result_matrix * self.cost_matrix) / np.sum(self.result_matrix)

    def get_parameters(self, model):
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        with open(path + '/parameters.yml', 'r') as yml:
            path = yaml.safe_load(yml)
        return path['distribution'][model]
