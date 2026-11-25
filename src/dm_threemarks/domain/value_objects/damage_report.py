# -*- coding: utf-8 -*-
from __future__ import absolute_import


class DamageReport(object):
    """Combined battle damage & assist telemetry snapshot."""

    __slots__ = (
        'damage', 'radio', 'track', 'stun', 'allies',
        'eff_damage', 'eff_assist', 'eff_stun', 'source',
    )

    def __init__(self, damage=0, radio=0, track=0, stun=0, allies=0,
                 eff_damage=0, eff_assist=0, eff_stun=0, source='efficiency'):
        self.damage = int(damage or 0)
        self.radio = int(radio or 0)
        self.track = int(track or 0)
        self.stun = int(stun or 0)
        self.allies = int(allies or 0)
        self.eff_damage = int(eff_damage or 0)
        self.eff_assist = int(eff_assist or 0)
        self.eff_stun = int(eff_stun or 0)
        self.source = str(source or 'efficiency')

    def combined(self):
        if self.source == 'feedback':
            return max(0, self.damage + max(self.radio, self.track, self.stun) - self.allies)
        return max(0, self.eff_damage + max(self.eff_assist, self.eff_stun) - self.allies)

    def to_parts_dict(self):
        return {
            'damage': self.damage,
            'radio': self.radio,
            'track': self.track,
            'stun': self.stun,
            'allies': self.allies,
            'effDamage': self.eff_damage,
            'effAssist': self.eff_assist,
            'effStun': self.eff_stun,
            'src': self.source,
        }
