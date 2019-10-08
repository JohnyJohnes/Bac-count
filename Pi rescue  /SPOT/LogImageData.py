#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""

Author: Jeroen Veen
"""

import os
import numpy as np
import pandas as pd
from PyQt5.QtCore import (QObject, pyqtSlot)


class LogImageData(QObject):

    def __init__(self):
        super().__init__()
        self.filename = None

    @pyqtSlot(str)
    def setFilename(self, fname):
        self.filename = os.path.splitext(fname)[0]

    @pyqtSlot(np.ndarray, np.ndarray, np.ndarray)
    def start(self, image=None, IQM=None, blobData=None):
        if not(IQM is None):  # we have new data
            iQMHeader = ('cropLeft', 'cropTop', 'cropWidth', 'cropHeight', 'rotAngle [x100]', 'totRoIArea', 'nonRoILaplacian',
                         'row_grid_found', 'RMS_row_contrast', 'RMS_row_sharpnesss [x100]', 'mean_row', 'mean_row_not_mask',
                         'col_grid_found', 'RMS_col_contrast', 'RMS_col_sharpnesss [x100]', 'mean_col', 'mean_col_not_mask')
            df = pd.DataFrame([IQM], columns=iQMHeader)
            df.to_csv(self.filename + '_IQM.csv', index=False)
            print(df)
        if not(blobData is None):
            blobHeader = ('RoILeft', 'RoITop', 'RoIWidth', 'RoIHeight', 'RoILaplacian',
                          'blobArea', 'blobPerimeter', 'blobAvgIntensity')
            df = pd.DataFrame(blobData, columns=blobHeader)
            df.to_csv(self.filename + '_blobData.csv')
