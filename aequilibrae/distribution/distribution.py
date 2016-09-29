# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------
# Name:       TRIP DISTRIBUTION
# Purpose:    Implementing a series of algorithms for trip distribution.
#              1st stage: Iterative proportinal fitting, synthetic gravity with power and exponential functions
#              2nd stage: Friction factors and synthetic gravity with gamma function
#
# Author:      Pedro Camargo
# Website:    www.AequilibraE.com
# Repository:  
#
# Created:     29/09/2016
# Copyright:   (c) AequilibraE authors
# Licence:     See LICENSE.TXT
# -------------------------------------------------------------------------------

# The procedures implemented in this code are some of those suggested in
# Modelling Transport, 4th Edition
# Ortuzar and Willumsen, Wiley 2011

# The referred authors have no responsibility over this work, of course

import numpy as np

def main():
    pass

class IterPropFit(WorkerThreadDistribution):
    def __init__(self, parentThread, matrix, prod, atra, max_error, max_itera):
        WorkerThreadDistribution.__init__(self, parentThread)
        self.matrix = matrix
        self.prod = prod
        self.atra = atra
        self.max_error = max_error
        self.max_itera = max_itera
        self.evol_bar = 2

    def doWork(self):
        matrix = self.matrix
        prod = self.prod
        atra = self.atra
        max_error = self.max_error
        max_itera = self.max_itera
        evol_bar = self.evol_bar
        self.error = None
        target = 100000000
        stepP = target / 100

        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (evol_bar, self.max_itera))
        count = 0

        tt = time.clock()
        # We guarantee that we enter the iterative process
        error = max_error + 1
        itera = 0

        # We will ignore all errors as we are treating them explicitly
        np.seterr(all='ignore')
        # We check if dimensions are correct
        if matrix.shape[1] == atra.shape[0] and matrix.shape[0] == prod.shape[0]:

            # And if the vectors are balanced up to 6 decimals
            if round(np.sum(prod), 6) == round(np.sum(atra), 6):

                # Start iterating
                while error > max_error and itera < max_itera:
                    self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, int(itera)))
                    self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"),
                              (evol_bar, "Convergence error: " + str(round(error, 8))))

                    # computes factors for rows
                    marg_rows = tot_rows(matrix)
                    row_factor = factor(marg_rows, prod)

                    # applies factor
                    matrix = np.transpose(np.transpose(matrix) * np.transpose(row_factor))

                    # computes factors for columns
                    marg_cols = tot_columns(matrix)
                    column_factor = factor(marg_cols, atra)

                    # applies factor
                    matrix = matrix * column_factor

                    # increments iterarions and computes errors
                    itera = itera + 1
                    error = max(1 - np.min(row_factor), np.max(row_factor) - 1, 1 - np.min(column_factor),
                                np.max(column_factor) - 1)

                text = "Error of " + str(round(error * 100, 10)) + '% reached after ' + str(
                    itera) + ' iterations and in ' + str(round(time.clock() - tt, 0)) + ' seconds'

                if itera < max_itera:
                    self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"),
                              (evol_bar, "Converged error: " + str(round(error, 6))))
                    self.result_matrix = matrix
                    self.logfile = text
                else:
                    self.result_matrix = None
                    self.error = "Procedure did not converge after " + str(itera) + " iterations"
            else:
                self.error = "Production and Attraction vectors are not balanced"
        else:
            self.error = "Seed matrix, production and attraction vectors do not have compatible dimensions"

        self.procedure = "FRATAR FINISHED"
        self.emit(SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"), self.procedure)


class GravityApplication(WorkerThreadDistribution):
    def __init__(self, parentThread, vectors, imp_matrix, parameters, max_cost, max_error, max_iter):
        WorkerThreadDistribution.__init__(self, parentThread)
        self.vectors = vectors
        self.imp_matrix = imp_matrix
        self.parameters = parameters
        self.max_cost = max_cost
        self.max_error = max_error
        self.max_iter = max_iter
        self.evol_bar = 2

    def doWork(self):
        prod = self.vectors[0]
        atra = self.vectors[1]
        self.error = None
        cost = self.imp_matrix
        max_cost = self.max_cost
        evol_bar = self.evol_bar

        if cost.shape[1] == atra.shape[0] and cost.shape[0] == prod.shape[0]:

            self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Initializing model"))
            matrix = np.zeros_like(cost)

            # We apply the function
            self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (evol_bar, prod.shape[0]))
            self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Applying model"))
            for i in range(prod.shape[0]):
                self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, i))
                matrix[i, :] = self.apply_function(cost[i, :], prod[i], atra[:])

            use_cost = (cost < max_cost).astype(int)

            # We zero all the cells that are in places were the cost is too high
            # This step is more useful for the calibration, but it can be used for
            # model application as well

            if max_cost != None:
                self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Eliminating cells above maximum cost"))
                a = (cost < max_cost).astype(int)
                matrix = a * matrix

            # We adjust the total of the matrix
            self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Adjusting matrix total"))
            matrix = matrix * np.sum(prod) / np.sum(matrix)

            # And adjust with a fratar
            self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (evol_bar, self.max_iter))

            self.matrix = matrix
            self.fratar()

            self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, self.max_iter))

        else:
            self.error = "Seed matrix, production and attraction vectors do not have compatible dimensions"

        self.procedure = "GRAVITY APPLICATION FINISHED"
        self.emit(SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"), self.procedure)

    def apply_function(self, cost, p, a):
        function = self.parameters[0]
        alfa = self.parameters[1]
        beta = self.parameters[2]
        friction = self.parameters[3]

        if function == "EXPO":
            f = np.exp(-beta * cost) * p * a
        elif function == "POWER":
            f = np.power(cost, -alfa) * p * a


        elif function == "GAMMA":
            f = np.power(cost, alfa) * np.exp(-beta * cost) * p * a
        else:
            pass
            # HERE WE NEED TO IMPLEMENT FRICTION FACTORS
        infinites = np.isinf(f).astype(int)
        non_inf = np.ones_like(f) - infinites
        f = f * non_inf
        return np.nan_to_num(f)

    def fratar(self):
        prod = self.vectors[0]
        atra = self.vectors[1]
        matrix = self.matrix
        max_error = self.max_error
        max_itera = self.max_iter
        evol_bar = self.evol_bar

        # We guarantee that we enter the iterative process
        error = max_error + 1
        itera = 0

        # We will ignore all errors as we are treating them explicitly
        np.seterr(all='ignore')

        # Start iterating
        while error > max_error and itera < max_itera:
            self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, int(itera)))
            self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Current error: " + str(round(error, 8))))
            # computes factors for rows
            marg_rows = tot_rows(matrix)
            row_factor = factor(marg_rows, prod)

            # applies factor
            matrix = np.transpose(np.transpose(matrix) * np.transpose(row_factor))

            # computes factors for columns
            marg_cols = tot_columns(matrix)
            column_factor = factor(marg_cols, atra)

            # applies factor
            matrix = matrix * column_factor

            # increments iterarions and computes errors
            itera = itera + 1
            error = max(1 - np.min(row_factor), np.max(row_factor) - 1, 1 - np.min(column_factor),
                        np.max(column_factor) - 1)
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Converged error: " + str(round(error, 8))))
        self.text = "Error of ", round(error * 100, 8), '% reached after ', itera, ' iterations\n'


class GravityCalibration(WorkerThreadDistribution):
    def __init__(self, parentThread, matrix, cost, function, max_iter, max_error, max_cost):
        WorkerThreadDistribution.__init__(self, parentThread)
        self.matrix = matrix
        self.orig_matrix = self.matrix.copy()
        self.vectors = (tot_rows(matrix), tot_columns(matrix))

        self.cost = cost
        self.function = function
        self.max_iter = max_iter
        self.max_error = max_error
        self.max_cost = max_cost
        self.error = None
        self.evol_bar = 2
        print 'init done'

    def doWork(self):
        matrix = self.matrix
        orig_matrix = self.orig_matrix
        cost = self.cost
        function = self.function
        max_cost = self.max_cost
        evol_bar = self.evol_bar

        if cost.shape[0] == matrix.shape[0] and cost.shape[1] == matrix.shape[1]:
            try:

                self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Initializing model calibration"))

                self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (evol_bar, self.max_iter))
                self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Calibration iterations"))

                # Number of steps in the computation of each iteration
                self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (evol_bar + 1, 3))

                error, itera = [1, 0]
                if function in ["EXPO", "POWER"]:
                    # The average cost gives an idea on which parameter to pick
                    avg_cost = np.sum(orig_matrix * cost) / np.sum(orig_matrix)

                    b0 = 1 / avg_cost
                    # print avg_cost, b0
                    self.parameters = (function, b0, b0, 0)
                    c0 = self.apply_model()
                    self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar + 1, 1))

                    b1 = b0 * c0 / avg_cost
                    self.parameters = (function, b1, b1, 0)
                    c1 = self.apply_model()
                    # print c1, b1
                    error = abs(c1 / avg_cost - 1)
                    self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar + 1, 2))

                    itera = 2
                    while error > self.max_error and itera < self.max_iter:
                        itera += 1
                        b_aux = b1
                        b1 = ((avg_cost - c0) * b1 - (avg_cost - c1) * b0) / (c1 - c0)
                        b0 = b_aux
                        c0 = c1

                        self.parameters = (function, b1, b1, 0)
                        c1 = self.apply_model()
                        # print c1,b1
                        error = abs(c1 / avg_cost - 1)
                        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, itera))

                self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Eliminating cells above maximum cost"))
                self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (evol_bar, self.max_iter))
                self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, self.max_iter))

            except:
                self.error = "Calibration procedure returned an error"
        else:
            self.error = "Observed matrix and cost matrix do not have the same dimensions"
        self.text = "Converged in " + str(itera) + "  iterations to a global error of " + str(error)
        self.procedure = "GRAVITY CALIBRATION FINISHED"
        self.emit(SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"), self.procedure)

    def apply_model(self):
        prod, atra = self.vectors
        matrix = self.matrix
        cost = self.cost
        evol_bar = self.evol_bar + 1
        # Apply the model for the current parameters' values
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Applying model"))
        for i in range(prod.shape[0]):
            matrix[i, :] = self.apply_function(cost[i, :], prod[i], atra[:])
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, 1))

        # Adjust marginals
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Adjusting matrix through IPF"))
        self.fratar()
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, 2))

        # compute average cost C
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Computing convergence"))
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, 3))
        c = np.sum(matrix * cost) / np.sum(matrix)

        return c

    def apply_function(self, cost, p, a):
        function = self.parameters[0]
        alfa = self.parameters[1]
        beta = self.parameters[2]
        friction = self.parameters[3]
        evol_bar = self.evol_bar

        if function == "EXPO":
            f = np.exp(-beta * cost) * p * a
        elif function == "POWER":
            f = np.power(cost, -alfa) * p * a


        elif function == "GAMMA":
            f = np.power(cost, alfa) * np.exp(-beta * cost) * p * a
        else:
            pass
            # HERE WE NEED TO IMPLEMENT FRICTION FACTORS
        infinites = np.isinf(f).astype(int)
        non_inf = np.ones_like(f) - infinites
        f = f * non_inf
        return np.nan_to_num(f)

    def fratar(self):
        prod = self.vectors[0]
        atra = self.vectors[1]
        matrix = self.matrix

        # We guarantee that we enter the iterative process
        error = self.max_error + 1
        itera = 0

        # We will ignore all errors as we are treating them explicitly
        np.seterr(all='ignore')

        # Start iterating
        while error > self.max_error and itera < self.max_iter:
            self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, int(itera)))
            self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Current error: " + str(round(error, 8))))
            # computes factors for rows
            marg_rows = tot_rows(matrix)
            row_factor = factor(marg_rows, prod)

            # applies factor
            matrix = np.transpose(np.transpose(matrix) * np.transpose(row_factor))

            # computes factors for columns
            marg_cols = tot_columns(matrix)
            column_factor = factor(marg_cols, atra)

            # applies factor
            matrix = matrix * column_factor

            # increments iterarions and computes errors
            itera = itera + 1
            error = max(1 - np.min(row_factor), np.max(row_factor) - 1, 1 - np.min(column_factor),
                        np.max(column_factor) - 1)
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Converged error: " + str(round(error, 8))))
        text = "Error of ", round(error * 100, 8), '% reached after ', itera, ' iterations\n'
        self.text = text


class WriteMatrix(WorkerThreadDistribution):
    def __init__(self, parentThread, result_matrix, result_file):
        WorkerThreadDistribution.__init__(self, parentThread)
        self.result_matrix = result_matrix
        self.result_file = result_file
        self, evol_bar = 3

    def doWork(self):
        result_matrix = self.result_matrix
        evol_bar = self.evol_bar
        non_zeros = np.transpose(np.nonzero(result_matrix))
        featcount = non_zeros.shape[0]
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (evol_bar, featcount))
        P = 0
        o = open(self.result_file, 'w')
        print >> o, 'FROM,TO,FLOW'
        for i, j in non_zeros:
            P = P + 1
            if P % 1000 == 0:
                self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, int(P)))
                self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"),
                          (evol_bar, "Writing results: " + str(P) + "/" + str(featcount)))
            print >> o, i, ',', j, ',', result_matrix[i, j]
        o.flush()
        o.close()
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, eatcount))
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, "Procedure finalized"))


def tot_rows(matrix):
    return np.sum(matrix, axis=1)


def tot_columns(matrix):
    return np.sum(matrix, axis=0)


def factor(marginals, targets):
    f = np.divide(targets, marginals)  # We compute the factors
    f[f == np.NINF] = 1  # And treat the errors, with the infinites first
    f = f + 1  # and the NaN second
    f = np.nan_to_num(f)  # The sequence of operations is just a resort to
    f[f == 0] = 2  # use at most numpy functions as possible instead of pure Python
    f = f - 1
    return f


if __name__ == '__main__':
    main()
