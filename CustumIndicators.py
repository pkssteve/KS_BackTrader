import backtrader as bt
import math

class VolumeRatio(bt.Indicator):
    lines = ('vr',)
    params = (('period', 14),)
    iterval = 0

    def next(self):
        self.iterval += 1
        self.data.upvol[0] = self.data.volume[0] if self.data.close[0] > self.data.close[-1] else self.data.volume[0] / 2 if self.data.close[0] == self.data.close[-1] else 0

        if self.iterval > self.p.period:
            sumupvol = sum(self.data.upvol.get(size=self.p.period))
            sumdownvol = sum(self.data.volume.get(size=self.p.period))
            self.lines.vr[0] = 100*(sumupvol/sumdownvol)