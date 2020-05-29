"""Defines the list of DVR libraries available."""

import os

__all__ = []
for item in os.listdir( os.path.dirname( os.path.abspath( __file__ ) ) ):
    if item.endswith( '.py' ) and item != '__init__.py':
      __all__.append( item[:-3] )
