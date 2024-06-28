import importlib.util as iutil
import sys
import textwrap

from datetime import datetime as dt

from qgis.core import QgsProcessingAlgorithm, QgsProcessingMultiStepFeedback, QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterDefinition, QgsProcessingParameterBoolean, QgsProcessingParameterString

from qaequilibrae.i18n.translate import trlt

class MatrixCalculator(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "conf_file",
                self.tr("Matrix configuration file (.yaml)"),
                behavior=QgsProcessingParameterFile.File,
                fileFilter="*.yaml",
                defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                "request",
                self.tr("Request"),
                multiLine=False,
                defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                "dest_path",
                self.tr("Existing .aem file")+self.tr("(used to store computed matrix)"),
                behavior=QgsProcessingParameterFile.File,
                fileFilter="*.aem",
                defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                "matrix_core",
                self.tr("Matrix core"),
                multiLine=False, 
                defaultValue="MatrixCalculator_Result"
            )
        )
        
        advparams = [
            QgsProcessingParameterString(
                "filtering_matrix",
                self.tr("Filtering matrix"),
                multiLine=False,
                defaultValue=None
            )
        ]
        
        for param in advparams:
            param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
            self.addParameter(param)

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(4, model_feedback)

        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae.matrix import AequilibraeMatrix
        import numpy as np
        import yaml
        
        start=dt.now()
        
        # Import or create all needed matrices as numpy arrays
        feedback.pushInfo(self.tr("Getting matrices from configuration file"))
        conf_file = parameters["conf_file"]
        dest_path = parameters["dest_path"]
        dest_core = parameters["matrix_core"]
        
        destination=AequilibraeMatrix()
        destination.load(dest_path)
        d=len(destination.get_matrix(dest_core))

        feedback.pushInfo(self.tr("Matrix total before calculation: ")+"{:,.2f}".format(destination.get_matrix(dest_core).sum()).replace(",", " "))
        feedback.pushInfo(self.tr("Expected dimensions of matrix based on destination file: ")+str(d)+"x"+str(d))
        feedback.pushInfo("")
        
        with open(conf_file, "r") as f:
            params = yaml.safe_load(f)
        m_list=[]

        for matrices in params["Matrices"]:
            for matrix in matrices:
                exec(matrix + "= AequilibraeMatrix()")
                exec(matrix + ".load('"+matrices[matrix]["matrix_path"]+"')")
                exec(matrix + "="+matrix+ ".get_matrix('"+matrices[matrix]["matrix_core"]+"')")

                m_list.append(matrix)
                exec("dim=len("+matrix+")")
                feedback.pushInfo(self.tr(f"Importation of {matrix}, matrix dimensions {dim}x{dim} and total is:"))
                exec('print("{:,.2f}".format('+matrix+'.sum()).replace(",", " "))')
                print()
                assert d==dim, self.tr("Matrices must have the same dimensions as the desired result !")

        if "null_diag" in request: # If needed, prepare a matrix to set diagonal to 0
            null_diag=np.ones((d, d), dtype=np.float64)
            np.fill_diagonal(null_diag, 0)

        if "zeros" in request: # If needed, prepare a matrix full of zero
            zeros=np.zeros((d, d), dtype=np.float64)    
        feedback.pushInfo(" ")
        feedback.setCurrentStep(1)

        # Setting up request, Used grammar is close to R language, need to be translated for numpy
        request=parameters["request"]
        
        request=request.replace("max(","np.maximum(")
        request=request.replace("min(","np.minimum(")
        request=request.replace("ln(","np.log(")
        request=request.replace("exp(","np.exp(")
        request=request.replace("power(","np.power(")
        request=request.replace("abs(","np.absolute(")
        request=request.replace("null_diag(","null_diag*(")
        request=request.replace("t(","np.transpose(")

        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)

        # Compute request: if a filtering matrix is used, update only a part of the destination matrix
        filtering_matrix=parameters["filtering_matrix"]
        if len(filtering_matrix)>0:
            exec("filtering_matrix=np.nan_to_num("+filtering_matrix+")")
            assert (np.any((filtering_matrix == 0.) | (filtering_matrix == 1.)))
            keep=np.absolute(filtering_matrix-np.ones(d))*destination.get_matrix(dest_core)
            exec("new=filtering_matrix*(" + request + ")")
            result=keep+new
            del filtering_matrix
        else:
            exec("result="+request)
        feedback.pushInfo(self.tr("Result (total: ")+f"{'{:,.2f}'.format(result.sum()).replace(',', ' ')}): ")
        feedback.pushInfo(str(result))

        feedback.pushInfo(" ")
        feedback.setCurrentStep(3)
        
        # Updating destination matrix file
        destination.matrix[dest_core][:,:] = result[:,:]
        destination.save()
        destination.close()
        
        for m in m_list :
            exec("del "+m)

        feedback.pushInfo(" ")
        feedback.setCurrentStep(4)

        return {"Output": self.tr("Calculation completed in: ")+str((dt.now()-start).total_seconds())+"secs"}

    def name(self):
        return self.tr("Matrix calculator")

    def displayName(self):
        return self.tr("Matrix calculator")

    def group(self):
        return ("02-"+self.tr("Data"))

    def groupId(self):
        return ("02-"+self.tr("Data"))

    def shortHelpString(self):
        return textwrap.dedent("\n".join([self.string_order(1), self.string_order(2), self.string_order(3), self.string_order(4), self.string_order(5), self.string_order(6), self.string_order(7), self.string_order(8), self.string_order(9)]))

    def createInstance(self):
        return MatrixCalculator()

    def string_order(self, order):
        if order == 1:
            return self.tr("Run a matrix calculation based on a request and a matrix config file (.yaml) :")
        elif order == 2:
            return self.tr("- Matrix configuration file (.yaml file)")
        elif order == 3:
            return (self.tr("- Request as a formula, example : ")+"null_diag( abs( max( t(matA)-(matB*3), zeros ) + power(matC,2) ) )")
        elif order == 4:
            return self.tr("- .aem file and matrix core to store calculated matrix")
        elif order == 5:
            return self.tr("- filtering matrix, a matrix of 0 and 1 defined in matrix config file that will be used to update only a part of the destination matrix ")
        elif order == 6:
            return self.tr("Example of valid matrix configuration file:")
        elif order == 7:
            return textwrap.dedent("""\
                Matrices:
                    - generation:
                        matrix_path: D:/AequilibraE/Project/matrices/socioeconomic_2024.aem
                        matrix_core: generation
                    - pop2024:
                        matrix_path: D:/AequilibraE/Project/matrices/socioeconomic_2024.aem
                        matrix_core: pop_dest
                    - emp2024:
                        matrix_path: D:/AequilibraE/Project/matrices/socioeconomic_2024.aem
                        matrix_core: emp_dest
                    - gen_time:
                        matrix_path: D:/AequilibraE/Project/matrices/aon_skims.aem
                        matrix_core: gen_time
               """)
        elif order == 8:
            return self.tr("List of available functions :")
        elif order == 9:
            return textwrap.dedent("""\
                    +
                    -
                    /
                    *
                    min(matA, matB)
                    max(matA, matB)
                    abs(matA)
                    ln(matA)
                    exp(matA)
                    power(matA, n)
                    null_diag(matA)
                    t(matA) #transpose
               """)
    def tr(self, message):
        return trlt("MatrixCalculator", message)
