"""
httpsql — a DB-API driver that reaches MySQL over HTTPS, so this dashboard can serve from Vercel
while its database stays on the Mac.

The problem it solves: a Vercel function cannot reach a MySQL on a laptop. It cannot join the
tailnet, and a database port must never be exposed to the internet. soma's Postgres apps already
solve this, but they solve it with `@neondatabase/serverless`, a JavaScript driver that POSTs SQL
to an HTTPS endpoint instead of speaking the wire protocol. There is no Python driver anywhere
that does the same, so this is that missing piece: the narrow part of PEP 249 SQLAlchemy actually
uses, implemented over one HTTP request per statement.

⭐ NOTHING IN THE APPLICATION CHANGES. SQLAlchemy keeps the `mysql+pymysql` dialect, so the SQL it
generates is the same MySQL it generated before; only the module that carries a statement to the
server is swapped. The endpoint is derived from the host in the connection string, the way Neon's
driver derives its own, so the whole configuration stays one URI:

    mysql+pymysql://<role>:<gateway token>@api.gkos.dev/<database>   ->  POST https://api.gkos.dev/mysql

⚠️ EVERY STATEMENT COMMITS ON ITS OWN, because there is no session on the far side: a request runs
one statement and the connection returns to the gateway's pool. `commit()` is therefore a no-op
and `rollback()` CANNOT undo a statement that has already been sent. Neon's HTTP endpoint
documents the same limitation for the Postgres apps. It is acceptable here because this dashboard
writes one row at a time and never needs two writes to stand or fall together. Anything that does
must run on the Mac, against the socket.
"""

import base64
import datetime
import json
import os
import urllib.error
import urllib.request
from decimal import Decimal

# PEP 249 module interface. "format" rather than pymysql's own "pyformat" because it is the
# simpler of the two to render exactly: SQLAlchemy then emits positional %s, and there are no
# named placeholders to resolve. The dialect reads this attribute and adapts.
apilevel = "2.0"
threadsafety = 1
paramstyle = "format"


class Error(Exception):
    pass


class Warning(Exception):  # noqa: A001 - the DB-API names it this
    pass


class InterfaceError(Error):
    pass


class DatabaseError(Error):
    pass


class DataError(DatabaseError):
    pass


class OperationalError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class InternalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


class NotSupportedError(DatabaseError):
    pass


# MySQL's own error numbers, so a failure raises the class the application would have caught
# before. A duplicate key has to arrive as IntegrityError or the ORM's own handling stops working.
_BY_ERRNO = {
    1022: IntegrityError, 1048: IntegrityError, 1052: IntegrityError,
    1062: IntegrityError, 1169: IntegrityError, 1216: IntegrityError,
    1217: IntegrityError, 1451: IntegrityError, 1452: IntegrityError,
    1054: ProgrammingError, 1064: ProgrammingError, 1146: ProgrammingError,
    1142: ProgrammingError, 1046: ProgrammingError, 1149: ProgrammingError,
    1044: OperationalError, 1045: OperationalError, 1040: OperationalError,
    1264: DataError, 1265: DataError, 1366: DataError, 1406: DataError,
}

# MySQL protocol type codes, the ones a column can come back as. The gateway sends dates and big
# numbers as text and tells us the type; rebuilding them here is what makes the values identical
# to the ones a local driver produced, which matters because the templates call .strftime() on
# them and arithmetic on the counts.
_DECIMAL, _TINY, _SHORT, _LONG, _FLOAT, _DOUBLE = 0, 1, 2, 3, 4, 5
_TIMESTAMP, _LONGLONG, _INT24, _DATE, _TIME, _DATETIME, _YEAR = 7, 8, 9, 10, 11, 12, 13
_NEWDATE, _BIT, _JSON, _NEWDECIMAL = 14, 16, 245, 246

_INTS = {_TINY, _SHORT, _LONG, _LONGLONG, _INT24, _YEAR}
_FLOATS = {_FLOAT, _DOUBLE}
_DECIMALS = {_DECIMAL, _NEWDECIMAL}


def _to_datetime(value):
    # MySQL admits '0000-00-00 00:00:00', which is not a date any calendar has. A local driver
    # answers None for it rather than raising, and so does this.
    text = value.strip()
    if text.startswith("0000-00-00"):
        return None
    for shape in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(text, shape)
        except ValueError:
            continue
    return value


def _to_time(value):
    # TIME is a duration in MySQL, not a clock reading: it may be negative and may exceed 24
    # hours, so it becomes a timedelta exactly as a local driver would give it.
    text = value.strip()
    sign = -1 if text.startswith("-") else 1
    parts = text.lstrip("-").split(":")
    try:
        hours, minutes = int(parts[0]), int(parts[1])
        seconds = float(parts[2]) if len(parts) > 2 else 0.0
    except (ValueError, IndexError):
        return value
    return sign * datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)


def _convert(value, type_code):
    if value is None:
        return None
    if isinstance(value, dict) and "$b64" in value:
        raw = base64.b64decode(value["$b64"])
        return raw
    if type_code in _INTS:
        return int(value)
    if type_code in _FLOATS:
        return float(value)
    if type_code in _DECIMALS:
        return Decimal(str(value))
    if type_code in (_DATETIME, _TIMESTAMP):
        return _to_datetime(value) if isinstance(value, str) else value
    if type_code in (_DATE, _NEWDATE):
        parsed = _to_datetime(value) if isinstance(value, str) else value
        return parsed.date() if isinstance(parsed, datetime.datetime) else parsed
    if type_code == _TIME:
        return _to_time(value) if isinstance(value, str) else value
    return value


def _encodable(value):
    """Put a bound parameter into something JSON can carry without losing what it was."""
    if isinstance(value, (bytes, bytearray)):
        return {"$b64": base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] if value.microsecond else value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, datetime.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, datetime.timedelta):
        total = int(value.total_seconds())
        sign = "-" if total < 0 else ""
        total = abs(total)
        return f"{sign}{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"
    if isinstance(value, Decimal):
        return str(value)
    return value


def _render(sql, args):
    """Turn the dialect's `%s` placeholders into the gateway's `?`, keeping the arguments bound.

    This mirrors what a local driver does with the format paramstyle, including leaving the
    statement completely alone when there are no arguments — a statement carrying a literal `%%`
    and no parameters is not substituted there either, and behaving differently would change SQL
    the application has always sent.
    """
    if args is None:
        return sql, []
    out, params, i, taken = [], [], 0, 0
    while i < len(sql):
        char = sql[i]
        if char == "%" and i + 1 < len(sql):
            following = sql[i + 1]
            if following == "%":
                out.append("%")
                i += 2
                continue
            if following == "s":
                out.append("?")
                params.append(_encodable(args[taken]) if taken < len(args) else None)
                taken += 1
                i += 2
                continue
        out.append(char)
        i += 1
    return "".join(out), params


def _raise(payload):
    errno = payload.get("errno")
    message = payload.get("message") or "database error"
    raise _BY_ERRNO.get(errno, ProgrammingError if errno else OperationalError)(errno, message)


class Cursor:
    def __init__(self, connection):
        self._connection = connection
        self._rows = []
        self._at = 0
        self.description = None
        self.rowcount = -1
        self.lastrowid = None
        self.arraysize = 1

    # SQLAlchemy closes cursors it is finished with; there is nothing on the far side to release,
    # because the statement already finished and its connection already went back to the pool.
    def close(self):
        self._rows, self._at = [], 0

    def execute(self, sql, args=None):
        statement, params = _render(sql, args)
        answer = self._connection._post(statement, params)
        columns = answer.get("columns") or []
        self.description = tuple(
            (column["name"], column["type"], None, None, None, None, None) for column in columns
        ) or None
        types = [column["type"] for column in columns]
        self._rows = [
            tuple(_convert(value, types[index]) for index, value in enumerate(row))
            for row in answer.get("rows") or []
        ]
        self._at = 0
        self.rowcount = answer.get("rowCount", -1)
        self.lastrowid = answer.get("lastRowId") or None
        return self.rowcount

    def executemany(self, sql, seq_of_args):
        # One request per row. A batch endpoint would be faster, and would also have to decide what
        # to do when the fourth row of a batch fails, which is the transaction question this
        # gateway cannot answer. Slow and unambiguous beats fast and undefined.
        total = 0
        for args in seq_of_args:
            total += self.execute(sql, args) or 0
        self.rowcount = total
        return total

    def fetchone(self):
        if self._at >= len(self._rows):
            return None
        self._at += 1
        return self._rows[self._at - 1]

    def fetchmany(self, size=None):
        size = self.arraysize if size is None else size
        chunk = self._rows[self._at : self._at + size]
        self._at += len(chunk)
        return chunk

    def fetchall(self):
        chunk = self._rows[self._at :]
        self._at = len(self._rows)
        return chunk

    def setinputsizes(self, *_):
        pass

    def setoutputsize(self, *_):
        pass

    def __iter__(self):
        return iter(self.fetchall())


class Connection:
    def __init__(self, endpoint, connection_string, timeout):
        self._endpoint = endpoint
        self._connection_string = connection_string
        self._timeout = timeout
        self.closed = False

    def _post(self, sql, params):
        body = json.dumps({"sql": sql, "params": params}).encode("utf-8")
        request = urllib.request.Request(
            self._endpoint,
            data=body,
            method="POST",
            headers={
                "content-type": "application/json",
                "sql-connection-string": self._connection_string,
                # ⚠️ NOT DECORATION. The gateway sits behind Cloudflare, whose bot protection
                # refuses urllib's default signature outright: every statement came back as
                # "error code: 1010" with a 403, which reads as an authorisation problem at the
                # gateway and is nothing of the kind. Naming the client is what gets a
                # machine-to-machine request past a check meant for browsers.
                "user-agent": "httpsql/1.0 (+drkostas dashboards)",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as failure:
            raw = failure.read().decode("utf-8", "replace")
            try:
                _raise(json.loads(raw))
            except json.JSONDecodeError:
                raise OperationalError(failure.code, raw[:500]) from failure
        except urllib.error.URLError as failure:
            # The gateway being unreachable is not a SQL error, and reporting it as one sends
            # whoever reads the log hunting through a query that was never the problem.
            raise OperationalError(2003, f"cannot reach the database gateway: {failure.reason}") from failure

    def cursor(self):
        return Cursor(self)

    # ⚠️ Both no-ops, and deliberately not exceptions: see the module docstring. Every statement
    # has already committed by the time either is called, so commit() has nothing left to do and
    # rollback() has nothing it can undo.
    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = True

    def ping(self, reconnect=True):  # noqa: ARG002 - the dialect passes False
        cursor = self.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        return True

    def character_set_name(self):
        # The dialect asks so it knows how to encode; the gateway and this module both speak
        # UTF-8 over JSON throughout, so there is nothing else it could be.
        return "utf8mb4"

    def autocommit(self, value):  # noqa: ARG002
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def connect(host=None, user=None, password=None, database=None, port=None, **_ignored):
    """Called by SQLAlchemy with the pieces of the URI. The endpoint is derived from the host."""
    host = host or os.getenv("DB_HOST") or "127.0.0.1"
    local = host in ("127.0.0.1", "localhost", "::1")
    scheme = "http" if local else "https"
    authority = f"{host}:{port}" if port else host
    endpoint = f"{scheme}://{authority}/mysql"
    # The gateway reads the role and the database from this string and the token from its
    # password, which is exactly what the URI already carries.
    connection_string = f"mysql://{user}:{password}@gw/{database}"
    return Connection(endpoint, connection_string, float(os.getenv("DB_GATEWAY_TIMEOUT", "20")))
