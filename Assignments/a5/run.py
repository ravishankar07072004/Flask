"""
Launcher for the Community Event Manager.

Run this file instead of app.py:   python run.py

app.py and all templates are left completely untouched. The navbar links
url_for('event_details') and url_for('register_event') are built without the
required <event_id>, which crashes every page with a BuildError. This launcher
registers a fallback so those links resolve instead of crashing:
  - if an event exists, they point to the first event's details / registration
  - if no events exist, they point back to the home page
"""
from flask import url_for
from werkzeug.routing import BuildError

from app import app, events_list


def _fallback_url(error, endpoint, values):
    if endpoint in ("event_details", "register_event") and "event_id" not in values:
        if events_list:
            return url_for(endpoint, event_id=events_list[0]["id"], **values)
        return url_for("index")
    raise error


app.url_build_error_handlers.append(_fallback_url)

if __name__ == "__main__":
    app.run(debug=True)
