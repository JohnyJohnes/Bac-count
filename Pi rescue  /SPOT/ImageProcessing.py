import cv2
import numpy as np
from PyQt5.QtCore import (QObject, pyqtSignal, pyqtSlot)
# from matplotlib import pyplot as plt


class ImageProcessing(QObject):
    ready = pyqtSignal(np.ndarray, np.ndarray, np.ndarray)

    def __init__(self):
        """
        ksize - Median Blur aperture linear size; it must be odd and greater than 1, for example: 3, 5, 7 ...
        adaptiveThresholdBlocksize -
        adaptiveThresholdOffset -
        showStep -
        annotate -
        """
        super().__init__()
        self.image = None
        self.cropXp1 = 0
        self.cropXp2 = 0
        self.cropYp1 = 0
        self.cropYp2 = 0
        self.rotAngle = 0.0
        self.gridSmoothKsize = 35
        self.gridMinSegmentLength = 50
        self.minBlobArea = 30
        self.maxBlobArea = 5000
        self.invertBinary = False
        self.ksize = 3
        self.blocksize = 3
        self.offset = 0
        self.showProcStep = 0
        self.annotateImage = True

    @pyqtSlot(int)
    def setMedianBlurKsize(self, ksize):
        if ksize > 1 and (ksize & 1) == 1:
            self.ksize = ksize
            self.start(None)
        else:
            print("Median Blur aperture linear size must be odd and greater than 1.")

    @pyqtSlot(int)
    def setAdaptiveThresholdBlocksize(self, blocksize):
        if blocksize > 1 and (blocksize & 1) == 1:
            self.blocksize = blocksize
            self.start(None)
        else:
            print("Adaptive threshold blocksize must be odd and greater than 1.")

    @pyqtSlot(int)
    def setAdaptiveThresholdOffset(self, offset):
        self.offset = offset  # if self.invertBinary else -offset
        self.start(None)

    @pyqtSlot(int)
    def setGridSmoothKsize(self, ksize):
        if ksize > 1 and (ksize & 1) == 1:
            self.gridSmoothKsize = ksize
            self.start(None)
        else:
            print("gridSmoothKsize size must be odd and greater than 1.")

    @pyqtSlot(int)
    def setGridMinSegmentLength(self, length):
        if length > 0:
            self.gridMinSegmentLength = length
            self.start(None)
        else:
            print("gridMinSegmentLength must be greater than 0.")

    @pyqtSlot(int)
    def setMinBlobArea(self, area):
        if area > 10:
            self.minBlobArea = area
            self.start(None)
        else:
            print("minBlobArea must be greater than 0.")

    @pyqtSlot(int)
    def setMaxBlobArea(self, area):
        if area > 0:
            self.maxBlobArea = area
            self.start(None)
        else:
            print("maxBlobArea must be greater than 0.")

    @pyqtSlot(int)
    def setProcStep(self, showStep):
        if showStep >= 0:
            self.showProcStep = showStep
            self.start(None)

    @pyqtSlot(int)
    def setAnnotate(self, annotate):
        self.annotateImage = True if annotate else False
        self.start(None)

    @pyqtSlot(int)
    def setInvertBinary(self, invert):
        self.invertBinary = True if invert else False
#        self.offset = self.offset if self.invertBinary else -self.offset
        self.start(None)

    @pyqtSlot(int)
    def setCropXp1(self, xp1):
        if xp1 > 0:
            self.cropXp1 = xp1
        self.start(None)

    @pyqtSlot(int)
    def setCropXp2(self, xp2):
        if xp2 > self.cropXp1:
            self.cropXp2 = xp2
        self.start(None)

    @pyqtSlot(int)
    def setCropYp1(self, yp1):
        if yp1 > 0:
            self.cropYp1 = yp1
        self.start(None)

    @pyqtSlot(int)
    def setCropYp2(self, yp2):
        if yp2 > self.cropYp1:
            self.cropYp2 = yp2
        self.start(None)

    @pyqtSlot(float)
    def setRotateAngle(self, angle):
        if angle > -5.0 and angle < 5.0:
            self.rotAngle = round(angle, 1)  # strange behaviour, so rounding is necessary
        self.start(None)

    @pyqtSlot(np.ndarray)
    def start(self, image=None):
        if not(image is None):  # we have a new image
            self.image = image
#            self.cropYp2, self.cropXp2 = (image.shape)[0:2]
        if not(self.image is None):
            # Preprocess the image
            rotImage = rotateImage(self.image, self.rotAngle)
            if self.cropXp2 > 0 and self.cropYp2 > 0:  # use the same crop as before
                cropImage = rotImage[self.cropYp1:self.cropYp2, self.cropXp1:self.cropXp2]
            else:
                cropImage = rotImage[self.cropYp1:(rotImage.shape)[
                    0], self.cropXp1:(rotImage.shape)[1]]
            grayImage = cv2.cvtColor(cropImage, cv2.COLOR_BGR2GRAY)
            blurredImage = cv2.medianBlur(grayImage, self.ksize)

            # Find grid pattern along row and column averages
            row_av = cv2.reduce(blurredImage, 0, cv2.REDUCE_AVG, dtype=cv2.CV_32S).flatten('F')
            row_grid_found, row_mask = self.findGrid(row_av)
            col_av = cv2.reduce(blurredImage, 1, cv2.REDUCE_AVG, dtype=cv2.CV_32S).flatten('F')
            col_grid_found, col_mask = self.findGrid(col_av)

            # Mask the grid, binarize and find blobs
            # masking first acts as a trick to combine all border blobs
            blurredImage[:, ~row_mask] = 0
            blurredImage[~col_mask, :] = 0
            BWImage = cv2.adaptiveThreshold(
                blurredImage, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, self.invertBinary, self.blocksize, self.offset)
            # connectedComponentsWithStats output: number of labels, label matrix, stats(left,top,width,height), area
            output = cv2.connectedComponentsWithStats(BWImage, 8, cv2.CV_32S)

            # Get blob RoI and area, and filter statistics
            tmpData = output[2][1:]  # skipping background (label 0)
            # Filter by area
            blobData = np.copy(tmpData[np.where(tmpData[:, 4] > self.minBlobArea)])
            blobData = blobData[np.where(blobData[:, 4] < self.maxBlobArea)]
            # # filter ratio of Area vs ROI, to remove border blobs
            # for index, row in enumerate(blobData):
            #     if (row[2] * row[3]) / row[4] > 8:
            #         print(row)
            #         blobData = np.delete(blobData, (index), axis=0)
            blobData = np.append(blobData, np.zeros(
                (blobData.shape[0], 3), dtype=int), axis=1)  # add empty columns

            # Compute metrics of individual blobs
            for row in blobData:
                tempImage = blurredImage[row[1]:row[1] + row[3], row[0]:row[0] + row[2]]
                tempBW = BWImage[row[1]:row[1] + row[3], row[0]:row[0] + row[2]]
                tempMask = tempBW > 0
                im2, contours, hierarchy = cv2.findContours(
                    tempBW, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)  # assuming that there is one blob in an RoI, if not we need to fiddle with the label output matrix output[1]
                row[5] = int(cv2.Laplacian(tempImage, cv2.CV_64F).var())  # local image quality
                row[6] = len(contours[0])  # perimeter
                row[7] = int(np.mean(tempImage[tempMask]))  # foreground mean intensity

            # Compute image metrics
            RMS_row_contrast = np.var(row_av)  # / np.mean(row_av)
            RMS_col_contrast = np.var(col_av)  # / np.mean(col_av)
#        est_I_max = np.mean(data[np.where(data > I_mean)])
#        est_I_min = np.mean(data[np.where(data < I_mean)])
#        contrast = (est_I_max-est_I_min) / 255 # relative amplitude wrt black-white pattern
            # Grid line gradient as a sharpness measure
            RMS_row_sharpnesss = 100 * \
                np.std(np.diff(row_av[~row_mask]))  # / np.mean(row_av[~row_mask])
            RMS_col_sharpnesss = 100 * \
                np.std(np.diff(col_av[~col_mask]))  # / np.mean(col_av[~col_mask])
            # grayImage[:, ~row_mask] = 0
            # grayImage[~col_mask, :] = 0
            laplacianVar = cv2.Laplacian(blurredImage, cv2.CV_64F).var()
            RoIArea = cv2.countNonZero(blurredImage)
            iQM = np.array((self.cropXp1, self.cropYp1, self.cropXp2 - self.cropXp1, self.cropYp2 - self.cropYp1,
                            100 * self.rotAngle, RoIArea, laplacianVar,
                            row_grid_found, RMS_row_contrast, RMS_row_sharpnesss,
                            np.mean(row_av), np.mean(row_av[~row_mask]),
                            col_grid_found, RMS_col_contrast, RMS_col_sharpnesss,
                            np.mean(col_av), np.mean(col_av[~col_mask])), dtype=int)

            # Compose Image signal
            if self.showProcStep == 0:
                img = cv2.cvtColor(cropImage, cv2.COLOR_BGR2RGB)
            elif self.showProcStep == 1:
                img = cv2.cvtColor(grayImage, cv2.COLOR_GRAY2RGB)
            elif self.showProcStep == 2:
                img = cv2.cvtColor(blurredImage, cv2.COLOR_GRAY2RGB)
            elif self.showProcStep == 3:
                img = cv2.cvtColor(BWImage, cv2.COLOR_GRAY2RGB)
            elif self.showProcStep == 4:
                img = cv2.cvtColor(BWImage, cv2.COLOR_GRAY2RGB)
            else:
                img = None
            if self.annotateImage:  # Annotate the image
                img[:, ~row_mask] = 0
                img[~col_mask, :] = 0
                for row in blobData:  # Show RoIs
                    tl = (row[0], row[1])
                    br = (row[0] + row[2], row[1] + row[3])
                    cv2.rectangle(img, tl, br, (255, 0, 0), 1)
            self.ready.emit(img, iQM, blobData)

    def findGrid(self, data):
        # high-pass filter, to suppress uneven illumination
        data = np.abs(data - moving_average(data, 111))
        # signal.savgol_filter(data, window_length=5, polyorder=2)
        smooth_data = moving_average(data, self.gridSmoothKsize)
        smooth_data = smooth_data - np.mean(smooth_data)
        mask_data = np.zeros(data.shape, dtype='bool')  # mask grid lines
        mask_data[np.where(smooth_data < 0)[0]] = True
        # Now filter mask_data based on segment length and suppress too short segments
        prev_x = False
        segmentLength = 0
        segmentList = []
        for index, x in enumerate(mask_data):
            if x:  # segment
                segmentLength += 1
            elif x != prev_x:  # falling edge
                if segmentLength < self.gridMinSegmentLength:  # suppress short segments
                    mask_data[index - segmentLength: index] = False
                    # print(diff(data[index - segmentLength:index]))
                else:
                    segmentList.append(segmentLength)
                segmentLength = 0  # reset counter
            prev_x = x
        segmentList = np.array(segmentList)
        # Rudimentary grid pattern recognition
        # expected pattern: 2 groups of 2 segments (+/- 5%), where the largest is sqrt(2) larger than smallest
        print(segmentList)
        gridFound = False
        if len(segmentList) >= 2 or len(segmentList) <= 10:  # Nr of segments should be reasonable
            # try to separate short and long segments, knn wouldbe better
            meanSegmentLength = np.mean(segmentList)
            shortSegments = segmentList[np.where(segmentList < meanSegmentLength)]
            longSegments = segmentList[np.where(segmentList > meanSegmentLength)]
            nrOfSegmentsRatio = 0  # define a measure for nr of short vs nr long segments
            if len(longSegments) > len(shortSegments):
                nrOfSegmentsRatio = len(shortSegments) / len(longSegments)
            elif len(shortSegments) > 0:
                nrOfSegmentsRatio = len(longSegments) / len(shortSegments)

            # n rOfSegmentsRatio = nrOfSegmentsRatio if nrOfSegmentsRatio <= 1.0 else 1 / nrOfSegmentsRatio
            if nrOfSegmentsRatio > 0.5:  # nr of short and long segments should be approximaely equal
                normSegmentLengthRatio = np.sqrt(2) * np.mean(shortSegments) / np.mean(longSegments)
                if normSegmentLengthRatio >= .9 and normSegmentLengthRatio <= 1.1:
                    gridFound = True

#        fig, ax = plt.subplots()
#        plt.plot(data)
#        plt.plot(smooth_data)
#        plt.plot(mask_data)
#        ax.grid(True)
#        plt.show(block=False)
        return (gridFound, mask_data)


def moving_average(x, N=5):
    if N > 1 and (N & 1) == 1:
        x = np.pad(x, pad_width=(round(N / 2) - 1, round(N / 2) - 1),
                   mode='constant')  # Assuming N is odd
        cumsum = np.cumsum(np.insert(x, 0, 0))
        return (cumsum[N:] - cumsum[:-N]) / float(N)
    else:
        print("Moving average size must be odd and greater than 1.")


def rotateImage(image, angle):
    if angle != 0:
        image_center = tuple(np.array(image.shape[1::-1]) / 2)
        rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
        result = cv2.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv2.INTER_LINEAR)
        return result
    else:
        return image
