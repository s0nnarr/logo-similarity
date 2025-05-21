class ImageAnalyzer:
    """
    Main class for a logo analyzer.
    This groups logos by similarities, using traditional computer vision algorithms.
    """
    
    def __init__(self, input_dir: str = ".", threshold: float = 0.75):
        """
        Params:
            input_dir: Location where the images have been downloaded by the scraper.
            threshold: The threshold that considers logos similar. (0.0 to 1.0)
        """
    
