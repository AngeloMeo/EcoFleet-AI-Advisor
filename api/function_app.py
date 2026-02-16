import azure.functions as func

from blueprints.telemetry import bp as telemetry_bp
from blueprints.advice import bp as advice_bp
from blueprints.vehicles import bp as vehicles_bp
from blueprints.admin import bp as admin_bp
from blueprints.signalr import bp as signalr_bp

app = func.FunctionApp()

app.register_functions(telemetry_bp)
app.register_functions(advice_bp)
app.register_functions(vehicles_bp)
app.register_functions(admin_bp)
app.register_functions(signalr_bp)
