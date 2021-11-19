class ConnectionAPINot200Error(ConnectionError):
    pass


class APIResponseNotDict(TypeError):
    pass


class NoHWStatusChangeError(Exception):
    pass


class ResponseHWsNotList(TypeError):
    pass


class ParseStatusKeyError(KeyError):
    pass


class ParseStatusValueError(ValueError):
    pass


class TokenError(Exception):
    pass
