"""
si_api - the API layer.

The only layer permitted to import si_core. It owns everything to do with transport
(schemas, routes, WebSockets, errors, CORS) and nothing to do with the domain: no
detection logic, no scoring rule, and no threshold lives here. If a number needs
deciding, it is decided in si_core and merely rendered here.
"""

__version__ = "1.0.0"