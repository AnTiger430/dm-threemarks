# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ..v3.samples import (
    PREVIEW_CONTAINER_H,
    PREVIEW_CONTAINER_W,
    PREVIEW_ORDER,
    PREVIEW_SAMPLES,
    PREVIEW_SAMPLES_V3,
)


class MenuPreviewRenderer(object):
    """Holds Mod Menu preview state and produces scaled live SVG data URIs."""

    def __init__(self, config_store, svg_renderer):
        self._config = config_store
        self._svg = svg_renderer
        self.state = {
            'state': 'plus',
            'uiState': 0,
            'alt': False,
            'hwAlt': False,
            'target': 0,
            'battleSection': 0,
            'battleSectionChanged': False,
            'hangarSection': 0,
            'hangarSectionChanged': False,
            'source': None,
            'key': None,
            'keyBattle': None,
            'keyHangar': None,
            'stateChangedBy': None,
            'syncing': False,
        }

    def apply_ui_controls(self, settings):
        ps = self.state
        prev_target = int(ps.get('target', 0) or 0)
        target_explicit = False
        ps['battleSectionChanged'] = False
        if 'battleSection' in settings:
            prev_bsec = int(ps.get('battleSection', 0) or 0)
            try:
                new_bsec = max(0, min(4, int(settings['battleSection'])))
            except (TypeError, ValueError):
                new_bsec = 0
            ps['battleSection'] = new_bsec
            ps['battleSectionChanged'] = (new_bsec != prev_bsec)
        ps['hangarSectionChanged'] = False
        if 'hangarSection' in settings:
            prev_sec = int(ps.get('hangarSection', 0) or 0)
            try:
                new_sec = max(0, min(3, int(settings['hangarSection'])))
            except (TypeError, ValueError):
                new_sec = 0
            ps['hangarSection'] = new_sec
            ps['hangarSectionChanged'] = (new_sec != prev_sec)
        if 'previewTarget' in settings:
            try:
                new_target = 1 if int(settings['previewTarget']) == 1 else 0
            except (TypeError, ValueError):
                new_target = 0
            target_explicit = (new_target != prev_target)
            ps['target'] = new_target
        ps['stateChangedBy'] = None
        for ctl_key in ('previewState', 'previewStateHangar'):
            if ctl_key in settings:
                try:
                    idx = max(0, min(len(PREVIEW_ORDER) - 1, int(settings[ctl_key])))
                except (TypeError, ValueError):
                    idx = 0
                if idx != ps.get('uiState'):
                    ps['uiState'] = idx
                    ps['state'] = PREVIEW_ORDER[idx]
                    ps['stateChangedBy'] = ctl_key
                    break
        if 'previewAlt' in settings:
            try:
                ps['alt'] = (int(settings['previewAlt']) == 1)
            except (TypeError, ValueError):
                ps['alt'] = False
        return target_explicit

    def render(self, target=None):
        st = self.state.get('state', 'plus')
        target = int(self.state.get('target', 0) or 0) if target is None else int(target)
        cfg_snap = self._config.snapshot()
        if target == 1:
            base_sample = PREVIEW_SAMPLES_V3.get(st) or PREVIEW_SAMPLES_V3['plus']
            h_sample = dict(base_sample)
            h_sample['isHangar'] = True
            h_sample['dmg'] = int(base_sample.get('tHold', 2450) or 2450)
            vh_scale = self._config.vh_scale()
            uri, width, height = self._svg.render_v3_svg(
                self._config.to_v3_from_hangar(cfg_snap), h_sample, alt=False,
            )
            scale = min(float(PREVIEW_CONTAINER_W) / float(width), float(PREVIEW_CONTAINER_H) / float(height), vh_scale)
            return uri, width, height, max(1, int(round(width * scale))), max(1, int(round(height * scale)))

        preset = self._config.integer('battlePreset', 0, 1)
        ui_scale = self._config.ui_scale()
        if preset == 0:
            sample = PREVIEW_SAMPLES_V3.get(st) or PREVIEW_SAMPLES_V3['plus']
            alt_active = bool(self.state.get('alt', False) or self.state.get('hwAlt', False))
            uri, width, height = self._svg.render_v3_svg(cfg_snap, sample, alt=alt_active)
        else:
            sample = PREVIEW_SAMPLES.get(st) or PREVIEW_SAMPLES['plus']
            uri, width, height = self._svg.render_classic_svg(self._config, sample, preset)
        scale = min(float(PREVIEW_CONTAINER_W) / float(width), float(PREVIEW_CONTAINER_H) / float(height), ui_scale)
        return uri, width, height, max(1, int(round(width * scale))), max(1, int(round(height * scale)))
