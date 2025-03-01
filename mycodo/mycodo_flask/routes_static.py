# coding=utf-8
import logging
import socket
import subprocess
import traceback

import flask_login
import operator
from flask import current_app
from flask import redirect
from flask import render_template
from flask import request
from flask import send_from_directory
from flask import url_for
from flask.blueprints import Blueprint

from mycodo.config import ALEMBIC_VERSION
from mycodo.config import LANGUAGES
from mycodo.config import MYCODO_VERSION
from mycodo.config import THEMES
from mycodo.config import THEMES_DARK
from mycodo.config_translations import TRANSLATIONS
from mycodo.databases.models import Dashboard
from mycodo.databases.models import Misc
from mycodo.mycodo_client import DaemonControl
from mycodo.mycodo_flask.forms import forms_dashboard
from mycodo.mycodo_flask.routes_authentication import admin_exists
from mycodo.mycodo_flask.utils.utils_general import user_has_permission

blueprint = Blueprint('routes_static',
                      __name__,
                      static_folder='../static',
                      template_folder='../templates')

logger = logging.getLogger(__name__)


def before_request_admin_exist():
    """
    Ensure databases exist and at least one user is in the user database.
    """
    if not admin_exists():
        return redirect(url_for("routes_authentication.create_admin"))
blueprint.before_request(before_request_admin_exist)


@blueprint.context_processor
def inject_variables():
    """Variables to send with every page request"""
    form_dashboard = forms_dashboard.DashboardConfig()  # Dashboard configuration in layout

    misc = Misc.query.first()

    try:
        if not current_app.config['TESTING']:
            control = DaemonControl()
            daemon_status = control.daemon_status()
        else:
            daemon_status = '0'
    except Exception as e:
        logger.debug("URL for 'inject_variables' raised and error: "
                     "{err}".format(err=e))
        daemon_status = '0'

    dashboards = []
    for each_dash in Dashboard.query.all():
        dashboards.append({
            'dashboard_id': each_dash.unique_id,
            'name': each_dash.name
        })

    languages_sorted = sorted(LANGUAGES.items(), key=operator.itemgetter(1))

    return dict(current_user=flask_login.current_user,
                dark_themes=THEMES_DARK,
                daemon_status=daemon_status,
                dashboards=dashboards,
                form_dashboard=form_dashboard,
                hide_alert_info=misc.hide_alert_info,
                hide_alert_success=misc.hide_alert_success,
                hide_alert_warning=misc.hide_alert_warning,
                hide_tooltips=misc.hide_tooltips,
                host=socket.gethostname(),
                languages=languages_sorted,
                mycodo_version=MYCODO_VERSION,
                permission_view_settings=user_has_permission('view_settings', silent=True),
                dict_translation=TRANSLATIONS,
                themes=THEMES,
                upgrade_available=misc.mycodo_upgrade_available)


@blueprint.route('/robots.txt')
def static_from_root():
    """Return static robots.txt"""
    return send_from_directory(current_app.static_folder, request.path[1:])


@blueprint.app_errorhandler(404)
def not_found(error):
    return render_template('404.html', error=error), 404


@blueprint.app_errorhandler(500)
def page_error(error):
    try:
        trace = traceback.format_exc()
    except:
        trace = None

    try:
        lsb_release = subprocess.Popen(
            "lsb_release -irdc", stdout=subprocess.PIPE, shell=True)
        (lsb_release_output, _) = lsb_release.communicate()
        lsb_release.wait()
        if lsb_release_output:
            lsb_release_output = lsb_release_output.decode("latin1").replace("\n", "<br/>")
    except:
        lsb_release_output = None

    try:
        model = subprocess.Popen(
            "cat /proc/device-tree/model && echo", stdout=subprocess.PIPE, shell=True)
        (model_output, _) = model.communicate()
        model.wait()
        if model_output:
            model_output = model_output.decode("latin1")
    except:
        model_output = None

    try:
        firmware = subprocess.Popen(
            "/opt/vc/bin/vcgencmd version", stdout=subprocess.PIPE, shell=True)
        (firmware_output, _) = firmware.communicate()
        firmware.wait()
        if firmware_output:
            firmware_output = firmware_output.decode("latin1").replace("\n", "<br/>")
    except:
        firmware_output = None

    dict_return = {
        "trace": trace,
        "version_mycodo": MYCODO_VERSION,
        "version_alembic":  ALEMBIC_VERSION,
        "lsb_release": lsb_release_output,
        "model": model_output,
        "firmware": firmware_output
    }
    return render_template('500.html', dict_return=dict_return), 500
