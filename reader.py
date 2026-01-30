import os
os.environ["DISABLE_MODEL_SOURCE_CHECK"] = "True"

from paddleocr import PaddleOCR
from ocr.preprocess import PlatePreprocessor
import re

class OCREngine:
    def __init__(self):
        self.ocr = PaddleOCR(
            lang="en",
            use_gpu=False,
            show_log=False
        )

    def read(self, img):
        out = []
        for var in PlatePreprocessor.generate(img):
            res = self.ocr.ocr(var, cls=False)
            if not res or not res[0]:
                continue
            for l in res[0]:
                txt = self._clean(l[1][0])
                conf = float(l[1][1])
                if self._valid(txt):
                    out.append((txt, conf))
        return out

    def _clean(self, t):
        t = re.sub(r"[^A-Z0-9]", "", t.upper())
        return t

    def _valid(self, t):
        return 5 <= len(t) <= 8 and any(c.isdigit() for c in t)
