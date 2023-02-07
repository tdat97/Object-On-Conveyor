from pypylon import pylon
import cv2

class BaslerCam():
    def __init__(self, ExposureTime=2500, logger=None):
        # conecting to the first available camera
        self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

        # Grabing Continusely (video) with minimal delay
        self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly) 
        self.converter = pylon.ImageFormatConverter()

        # converting to opencv bgr format
        self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

        # settimg ExposureTime
        self.camera.ExposureTime.SetValue(ExposureTime)
        
        if logger is not None:
            logger.info(f"Camera Name : {self.camera.GetDeviceInfo().GetModelName()}")
            logger.info(f"Exposure Time : {self.camera.ExposureTime.GetValue()}")
            logger.info(f"DeviceLinkThroughputLimit : {self.camera.DeviceLinkThroughputLimit.GetValue()}")

    def get_image(self):
        image = None
        if self.camera.IsGrabbing():
            grabResult = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if grabResult.GrabSucceeded():
                # Access the image data
                image = self.converter.Convert(grabResult)
                image = image.GetArray()
            grabResult.Release()
        return image

    def set_exposure(self, value):
        assert type(value) == int and 100 <= value <= 50000
        self.camera.ExposureTime.SetValue(value)

    def close(self):
        self.camera.StopGrabbing()
