import numpy as np
import cv2
from typing import Optional
from skimage.measure import label


class WatershedSegmenter:
    def __init__(
        self,
        low_q: float = 0.0,
        high_q: float = 0.98,
        filter_type: Optional[str] = None,
        filter_kernel: tuple = (5, 5),
        filter_sigma: float = 1.2,
        morph_kernel_size: int = 3,
        fg_thresh_ratio: float = 0.7,
        threshold_method: str = "adaptive",
        adaptive_th_method: str = "mean",
        adaptive_block_size: int = 7,
        adaptive_C: int = 2,
    ):
        self.low_q = low_q
        self.high_q = high_q
        self.filter_type = filter_type
        self.filter_kernel = filter_kernel
        self.filter_sigma = filter_sigma
        self.morph_kernel_size = morph_kernel_size
        self.fg_thresh_ratio = fg_thresh_ratio

        # Thresholding parameters (defaults kept here)
        self.threshold_method = threshold_method
        self.adaptive_th_method = adaptive_th_method
        self.adaptive_block_size = adaptive_block_size
        self.adaptive_C = adaptive_C

    # def segment(
    #     self,
    #     image: np.ndarray,
    #     threshold_method: Optional[str] = None,
    #     adaptive_th_method: Optional[str] = None,
    #     block_size: Optional[int] = None,
    #     C: Optional[int] = None,
    # ) -> np.ndarray:
    #     """
    #     Perform watershed segmentation and return binary contour mask.
    #
    #     Can override thresholding method and params on this call; else defaults used.
    #     """
    #     norm_img = self._normalize_image(image)
    #     filtered = self._apply_filter(norm_img)
    #
    #     # Use passed parameters or defaults
    #     method = threshold_method or self.threshold_method
    #     adapt_method = adaptive_th_method or self.adaptive_th_method
    #     block = block_size or self.adaptive_block_size
    #     c_val = C if C is not None else self.adaptive_C
    #
    #     thresh = self._apply_thresholding(
    #         filtered,
    #         method=method,
    #         block_size=block,
    #         C=c_val,
    #         adaptive_th_method=adapt_method,
    #     )
    #     markers = self._create_markers(thresh)
    #     contour_mask = self._apply_watershed(norm_img, markers)
    #     return contour_mask
    def segment(
            self,
            image: np.ndarray,
            threshold_method: Optional[str] = None,
            adaptive_th_method: Optional[str] = None,
            block_size: Optional[int] = None,
            C: Optional[int] = None,
    ) -> np.ndarray:

        print(f"segment, normalize, image type: {image.dtype}")
        norm_img = self._normalize_image(image)
        print("segment, filter")
        filtered = self._apply_filter(norm_img)

        method = threshold_method or self.threshold_method
        adapt_method = adaptive_th_method or self.adaptive_th_method
        block = block_size or self.adaptive_block_size
        c_val = C if C is not None else self.adaptive_C
        print(f"segment, thresh with {method}, block={block}, C={c_val}, adaptive={adapt_method}")
        thresh = self._apply_thresholding(
            filtered,
            method=method,
            block_size=block,
            C=c_val,
            adaptive_th_method=adapt_method,
        )
        print(f"segment, markers, image type: {thresh.dtype}")
        markers = self._create_markers(thresh)
        print(f"segment, watershed, image type: {markers.dtype}, {norm_img.dtype}, {markers.shape}, {norm_img.shape}")
        print(np.unique(markers))
        instance_mask = self._apply_watershed(norm_img, markers)
        print("segment, done")
        return instance_mask

    def _normalize_image(self, image: np.ndarray) -> np.ndarray:
        image = image.astype(np.float32)
        lower = np.quantile(image, self.low_q)
        upper = np.quantile(image, self.high_q)
        clipped = np.clip(image, lower, upper)
        norm = (clipped - lower) / (upper - lower)
        return (norm * 255).astype(np.uint8)

    def _apply_filter(self, image: np.ndarray) -> np.ndarray:
        if self.filter_type is None:
            return image

        if self.filter_type == "median":
            k = self.filter_kernel[0]
            return cv2.medianBlur(image, k)

        elif self.filter_type == "average":
            return cv2.blur(image, self.filter_kernel)

        elif self.filter_type == "gaussian":
            return cv2.GaussianBlur(image, self.filter_kernel, self.filter_sigma)

        elif self.filter_type == "bilateral":
            return cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)

        elif self.filter_type == "sobel":
            sobel = cv2.Sobel(image, cv2.CV_64F, dx=1, dy=0, ksize=3)
            # Convert back to uint8 scaled image to keep consistent output type
            abs_sobel = np.absolute(sobel)
            sobel_8u = np.uint8(255 * abs_sobel / np.max(abs_sobel))
            return sobel_8u

        else:
            raise ValueError(f"Unsupported filter type: {self.filter_type}")

    def _apply_thresholding(
        self,
        image: np.ndarray,
        method: str = "otsu",
        block_size: int = 11,
        C: int = 2,
        adaptive_th_method: str = "gaussian",
    ) -> np.ndarray:
        if image.ndim != 2:
            raise ValueError("Input image must be grayscale (2D array).")

        if block_size % 2 == 0 or block_size < 3:
            raise ValueError("Block size must be an odd integer > 1.")

        if image.dtype != np.uint8:
            image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        if method == "otsu":
            _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            return thresh

        elif method == "triangle":
            _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_TRIANGLE)
            return thresh

        elif method == "manual":
            _, thresh = cv2.threshold(image, 128, 255, cv2.THRESH_BINARY_INV)
            return thresh

        elif method == "adaptive":
            if adaptive_th_method == "gaussian":
                th_method = cv2.ADAPTIVE_THRESH_GAUSSIAN_C
            elif adaptive_th_method == "mean":
                th_method = cv2.ADAPTIVE_THRESH_MEAN_C
            else:
                raise ValueError("Invalid adaptive thresholding method.")
            thresh = cv2.adaptiveThreshold(image, 255, th_method, cv2.THRESH_BINARY, block_size, C)
            return thresh

        else:
            raise ValueError(f"Unsupported thresholding method: {method}")

    def _create_markers(self, thresh: np.ndarray) -> np.ndarray:
        kernel = np.ones((self.morph_kernel_size, self.morph_kernel_size), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
        sure_bg = cv2.dilate(opening, kernel, iterations=3)

        dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
        _, sure_fg = cv2.threshold(dist_transform, self.fg_thresh_ratio * dist_transform.max(), 255, 0)
        sure_fg = np.uint8(sure_fg)
        unknown = cv2.subtract(sure_bg, sure_fg)

        markers = label(sure_fg) + 1
        markers[unknown == 255] = 0
        return markers

    # def _apply_watershed(self, orig_image: np.ndarray, markers: np.ndarray) -> np.ndarray:
    #     color_img = cv2.cvtColor(orig_image, cv2.COLOR_GRAY2BGR)
    #     markers = cv2.watershed(color_img, markers)
    #
    #     contour_mask = np.zeros_like(orig_image, dtype=np.uint8)
    #     contour_mask[markers == -1] = 1
    #     return contour_mask

    def _apply_watershed(self, orig_image: np.ndarray, markers: np.ndarray) -> np.ndarray:
        # Normalize grayscale to uint8 for watershed
        if orig_image.dtype != np.uint8:
            orig_image = np.clip(orig_image * 255, 0, 255).astype(np.uint8)

        color_img = cv2.cvtColor(orig_image, cv2.COLOR_GRAY2BGR)

        if markers.dtype != np.int32:
            markers = markers.astype(np.int32)

        markers = cv2.watershed(color_img, markers)
        markers = markers - 1
        markers[markers < 0] = 0
        return markers.astype(np.uint16)