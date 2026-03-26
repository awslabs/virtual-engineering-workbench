import logging


def loggable_session(session, logger: logging.Logger):
    def log_boto3_request(params, event_name, **kwargs):
        try:
            event_type, service, action = event_name.split(".")

            if logger.log_level not in [logging.DEBUG, "DEBUG"]:
                logger.info(
                    {
                        "service": service,
                        "action": action,
                    }
                )
                return

            log_obj = dict()
            if service == "s3" and action == "PutObject":
                for key, value in params.items():
                    if key != "Body":
                        log_obj[key] = value
            else:
                log_obj = params

            logger.debug({"service": service, "action": action, "params": log_obj})
        except:
            logger.exception("Error logging boto3 request")

    session.events.register("provide-client-params", log_boto3_request)

    return session
