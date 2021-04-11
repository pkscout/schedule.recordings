import importlib
defaults = {'dvr_type': 'nextpvr',
            'dvr_host': '127.0.0.1',
            'dvr_port': '8866',
            'dvr_user': '',
            'dvr_auth': '0000',
            'dvr_params': {'recurring_type': 1},
            'tvmaze_user': '',
            'tvmaze_apikey': '',
            'tvmaze_wait': 0.12,
            'tvmaze_untag': True,
            'show_override': {},
            'lookforward': 10,
            'dateformat': '%Y-%m-%d',
            'aborttime': 30,
            'logbackups': 7,
            'debug': False}

try:
    import data.settings as overrides
    has_overrides = True
except ImportError:
    has_overrides = False


def Reload():
    if has_overrides:
        importlib.reload(overrides)


def Get(name):
    setting = None
    if has_overrides:
        setting = getattr(overrides, name, None)
    if not setting:
        setting = defaults.get(name, None)
    return setting
