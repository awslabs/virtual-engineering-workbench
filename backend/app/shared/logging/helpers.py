import copy

DICT_KEY_HEADERS = "headers"
DICT_KEY_MULTI_VALUE_HEADERS = "multiValueHeaders"
DICT_KEY_AUTHORIZATION = "Authorization"
DICT_KEY_REQUEST_CONTEXT = "requestContext"
DICT_KEY_AUTHORIZER = "authorizer"
DICT_KEY_USER_EMAIL = "userEmail"
DICT_KEY_USER_NAME = "userName"
MASKED_JWT = "***"


def clear_auth_headers(event: dict) -> dict:
    log_dict = copy.deepcopy(event)

    if DICT_KEY_HEADERS in log_dict and DICT_KEY_AUTHORIZATION in log_dict[DICT_KEY_HEADERS]:
        log_dict[DICT_KEY_HEADERS][DICT_KEY_AUTHORIZATION] = MASKED_JWT

    if DICT_KEY_MULTI_VALUE_HEADERS in log_dict and DICT_KEY_AUTHORIZATION in log_dict[DICT_KEY_MULTI_VALUE_HEADERS]:
        log_dict[DICT_KEY_MULTI_VALUE_HEADERS][DICT_KEY_AUTHORIZATION] = [
            MASKED_JWT for _ in log_dict[DICT_KEY_MULTI_VALUE_HEADERS][DICT_KEY_AUTHORIZATION]
        ]

    if DICT_KEY_REQUEST_CONTEXT in log_dict and DICT_KEY_AUTHORIZER in log_dict[DICT_KEY_REQUEST_CONTEXT]:
        authorizer = log_dict[DICT_KEY_REQUEST_CONTEXT][DICT_KEY_AUTHORIZER]
        if DICT_KEY_USER_EMAIL in authorizer:
            authorizer[DICT_KEY_USER_EMAIL] = MASKED_JWT
        if DICT_KEY_USER_NAME in authorizer:
            authorizer[DICT_KEY_USER_NAME] = MASKED_JWT

    return log_dict
