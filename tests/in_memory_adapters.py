# -*- coding: utf-8 -*-
from __future__ import absolute_import

from dm_threemarks.domain.entities.mark_snapshot import VehicleDossier
from dm_threemarks.application.ports.cache_repository import ICacheRepository
from dm_threemarks.application.ports.clock import IClock
from dm_threemarks.application.ports.config_repository import IConfigRepository
from dm_threemarks.application.ports.dossier_provider import IDossierProvider
from dm_threemarks.application.ports.hangar_environment import IHangarEnvironment
from dm_threemarks.application.ports.input_provider import IInputProvider
from dm_threemarks.application.ports.logger import ILogger
from dm_threemarks.application.ports.mastery_gateway import IMasteryGateway
from dm_threemarks.application.ports.panel_view import IPanelView
from dm_threemarks.application.ports.scheduler import IScheduler
from dm_threemarks.application.ports.settings_menu import ISettingsMenu


class MemoryConfigRepository(IConfigRepository):
    def __init__(self, initial=None):
        self.data = dict(initial) if isinstance(initial, dict) else {}
        self.mtime = 1.0
        self.help_written = None

    def load(self):
        return dict(self.data)

    def save(self, data):
        self.data = dict(data)

    def get_mtime(self):
        return self.mtime

    def write_help(self, mod_version, help_text):
        self.help_written = (mod_version, help_text)


class MemoryCacheRepository(ICacheRepository):
    def __init__(self, initial=None):
        self.data = dict(initial) if isinstance(initial, dict) else {}
        self.save_calls = 0

    def load(self):
        return dict(self.data)

    def save(self):
        self.save_calls += 1

    def get_entry(self, key):
        entry = self.data.get(key)
        if not isinstance(entry, dict):
            entry = {}
            self.data[key] = entry
        return entry

    def peek_entry(self, key):
        return self.data.get(key)

    def get_all(self):
        return self.data

    def replace_all(self, data):
        self.data = dict(data) if isinstance(data, dict) else {}


class MemoryMasteryGateway(IMasteryGateway):
    def __init__(self, available=True):
        self.available = available
        self.curve_requests = []
        self.history_requests = []
        self.queued = []

    def is_available(self):
        return self.available

    def request_curve(self, key, domain, app_id):
        self.curve_requests.append((key, domain, app_id))

    def request_history(self, key, domain):
        self.history_requests.append((key, domain))

    def drain_results(self):
        out = list(self.queued)
        del self.queued[:]
        return out


class MemoryDossierProvider(IDossierProvider):
    def __init__(self):
        self.dossiers = {}
        self.current_vehicle = None
        self.domain = 'eu'
        self.battle_ctx = None

    def read_dossier(self, int_cd):
        return self.dossiers.get(int_cd)

    def get_current_vehicle_info(self):
        return self.current_vehicle

    def get_realm_domain(self):
        return self.domain

    def get_player_battle_context(self):
        return self.battle_ctx


class MemoryPanelView(IPanelView):
    def __init__(self):
        self.built = False
        self.destroyed = False
        self.pushed = []
        self.hidden = False
        self.pos = (0.0, 0.0)
        self.mini = False
        self.settings_open = False
        self._settings_controller = None

    @property
    def settings_controller(self):
        return self._settings_controller

    def build(self):
        self.built = True
        self.destroyed = False

    def push(self, data):
        self.pushed.append(data)

    def destroy(self):
        self.destroyed = True

    def move_to(self, x, y):
        self.pos = (x, y)

    def contains(self, pos):
        return False

    def update_visibility(self, hidden=False):
        self.hidden = bool(hidden)

    def open_settings(self):
        self.settings_open = True

    def close_settings(self):
        self.settings_open = False

    def is_settings_open(self):
        return self.settings_open

    def set_mini(self, mini):
        self.mini = bool(mini)


class MemorySettingsMenu(ISettingsMenu):
    def __init__(self):
        self.registered = False
        self.push_calls = 0
        self.preview_calls = 0
        self.hw_alt = False

    def register(self):
        self.registered = True
        return True

    def unregister(self):
        self.registered = False

    def push_values(self):
        self.push_calls += 1

    def refresh_preview(self):
        self.preview_calls += 1

    def sync_tabs(self, force=False):
        return False

    def is_registered(self):
        return self.registered

    def set_hardware_alt(self, active):
        self.hw_alt = bool(active)

    def swap_settings_page(self, panel):
        pass


class FakeClock(IClock):
    def __init__(self, now=1700000000.0, server_now=1700000000.0, battle_time=10.0):
        self._now = now
        self._server_now = server_now
        self._battle_time = battle_time

    def now(self):
        return self._now

    def server_now(self):
        return self._server_now

    def battle_time(self):
        return self._battle_time

    def advance(self, seconds):
        self._now += seconds
        self._server_now += seconds
        self._battle_time += seconds


class MemoryLogger(ILogger):
    def __init__(self):
        self.infos = []
        self.errors = []
        self._seen = set()

    def info(self, msg):
        self.infos.append(msg)

    def once(self, key, msg):
        if key not in self._seen:
            self._seen.add(key)
            self.infos.append(msg)

    def error(self, where):
        self.errors.append(where)


class FakeInputProvider(IInputProvider):
    def __init__(self):
        self.alt = False
        self.ctrl = False
        self.tab = False
        self.lmb = False
        self.sniper = False
        self.intro = (False, '')
        self.killcam = (False, '')
        self.dead = (False, '')

    def is_alt_down(self):
        return self.alt

    def is_ctrl_down(self):
        return self.ctrl

    def is_tab_down(self):
        return self.tab

    def is_lmb_down(self):
        return self.lmb

    def cursor_position(self):
        return (0.0, 0.0)

    def screen_size(self):
        return (1920.0, 1080.0)

    def px_w(self, px):
        return px * 2.0 / 1920.0

    def px_h(self, px):
        return px * 2.0 / 1080.0

    def is_sniper_mode(self):
        return self.sniper

    def is_intro_active(self):
        return self.intro

    def is_killcam_active(self):
        return self.killcam

    def is_player_dead(self):
        return self.dead


class FakeScheduler(IScheduler):
    def __init__(self):
        self._next_id = 1
        self.scheduled = {}
        self.canceled = []

    def schedule(self, delay_sec, callback):
        hid = self._next_id
        self._next_id += 1
        self.scheduled[hid] = callback
        return hid

    def cancel(self, handle):
        self.canceled.append(handle)
        self.scheduled.pop(handle, None)


class FakeHangarEnvironment(IHangarEnvironment):
    def __init__(self):
        self.state = (True, 'hangar')
        self.mode = (True, 'random')
        self.covered = False
        self.views = set()

    def hangar_state(self):
        return self.state

    def hangar_mode(self):
        return self.mode

    def is_covered(self, own_window):
        return self.covered

    def view_class_names(self):
        return self.views
