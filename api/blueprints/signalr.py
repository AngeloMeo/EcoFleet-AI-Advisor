import azure.functions as func

bp = func.Blueprint()

@bp.route(route="negotiate", auth_level=func.AuthLevel.ANONYMOUS)
@bp.generic_input_binding(arg_name="connectionInfo", type="signalRConnectionInfo", hubName="telemetryHub", connectionStringSetting="SignalRConnectionString")
def negotiate(req: func.HttpRequest, connectionInfo: str) -> func.HttpResponse:
    return func.HttpResponse(connectionInfo)
