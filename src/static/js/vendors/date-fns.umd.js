!(function (t, e) {
  "object" == typeof exports && "undefined" != typeof module
    ? e(exports)
    : "function" == typeof define && define.amd
    ? define(["exports"], e)
    : e(
        ((t =
          "undefined" != typeof globalThis ? globalThis : t || self).dateFns =
          {})
      );
})(this, function (e) {
  "use strict";
  function t(e) {
    return (
      e instanceof Date || "[object Date]" === Object.prototype.toString.call(e)
    );
  }
  function n(e) {
    if (arguments.length < 1)
      throw new TypeError(
        "1 argument required, but only " + arguments.length + " present"
      );
    var n = Object.prototype.toString.call(e);
    return e instanceof Date || ("object" == typeof e && "[object Date]" === n)
      ? new Date(e.getTime())
      : "number" == typeof e || "[object Number]" === n
      ? new Date(e)
      : (("string" != typeof e && "[object String]" !== n) ||
          "undefined" == typeof console ||
          (console.warn(
            "Starting with v2.0.0-beta.1 date-fns doesn't accept strings as date arguments. Please use `parseISO` to parse strings. See: https://git.io/fjule"
          ),
          console.warn(new Error().stack)),
        new Date(NaN));
  }
  function r(e, t) {
    if (arguments.length < 2)
      throw new TypeError(
        "2 arguments required, but only " + arguments.length + " present"
      );
    var r = n(e),
      a = n(t),
      o = r.getTime() - a.getTime();
    return o < 0 ? -1 : o > 0 ? 1 : o;
  }
  function a(e, t) {
    if (arguments.length < 2)
      throw new TypeError(
        "2 arguments required, but only " + arguments.length + " present"
      );
    var a = n(e).getTime(),
      o = n(t).getTime();
    return a < o;
  }
  function o(e, t) {
    if (arguments.length < 2)
      throw new TypeError(
        "2 arguments required, but only " + arguments.length + " present"
      );
    var a = n(e).getTime(),
      o = n(t).getTime();
    return a > o;
  }
  function i(e, t) {
    if (arguments.length < 2)
      throw new TypeError(
        "2 arguments required, but only " + arguments.length + " present"
      );
    var r = n(e),
      a = n(t);
    return r.getFullYear() === a.getFullYear() && r.getMonth() === a.getMonth();
  }
  function u(e) {
    if (arguments.length < 1)
      throw new TypeError(
        "1 argument required, but only " + arguments.length + " present"
      );
    var t = n(e);
    return !isNaN(t);
  }
  function s(e, t) {
    if (arguments.length < 2)
      throw new TypeError(
        "2 arguments required, but only " + arguments.length + " present"
      );
    var r = n(e),
      a = n(t);
    return r.getTime() === a.getTime();
  }
  function c(e) {
    return e.getTime();
  }
  function d(e) {
    if (arguments.length < 1)
      throw new TypeError(
        "1 argument required, but only " + arguments.length + " present"
      );
    var r = n(e);
    return r.setHours(0, 0, 0, 0), r;
  }
  function f(e, t) {
    if (arguments.length < 2)
      throw new TypeError(
        "2 arguments required, but only " + arguments.length + " present"
      );
    var r = d(e),
      a = d(t);
    return r.getTime() === a.getTime();
  }
  function h(e, t) {
    if (arguments.length < 2)
      throw new TypeError(
        "2 arguments required, but only " + arguments.length + " present"
      );
    var r = n(e),
      a = n(t);
    return f(r, a);
  }
  function y(e) {
    return e.setHours(0, 0, 0, 0), e;
  }
  function m(e, t) {
    var n =
      e.getFullYear() - t.getFullYear() ||
      e.getMonth() - t.getMonth() ||
      e.getDate() - t.getDate() ||
      e.getHours() - t.getHours() ||
      e.getMinutes() - t.getMinutes() ||
      e.getSeconds() - t.getSeconds() ||
      e.getMilliseconds() - t.getMilliseconds();
    return n < 0 ? -1 : n > 0 ? 1 : n;
  }
  function l(e, t) {
    if (arguments.length < 2)
      throw new TypeError(
        "2 arguments required, but only " + arguments.length + " present"
      );
    var a = n(e),
      o = n(t),
      i = m(a, o),
      u = Math.abs(
        (function (e, t) {
          if (arguments.length < 2)
            throw new TypeError(
              "2 arguments required, but only " + arguments.length + " present"
            );
          var a = n(e),
            o = n(t);
          return (
            12 * (a.getFullYear() - o.getFullYear()) +
            (a.getMonth() - o.getMonth())
          );
        })(a, o)
      );
    return 0 === u ? 0 : i * u;
  }
  function g(e, r) {
    if (arguments.length < 2)
      throw new TypeError(
        "2 arguments required, but only " + arguments.length + " present"
      );
    var a = n(e),
      o = n(r),
      i = a.getTime() - o.getTime();
    return Math.round(i / 864e5);
  }
  function v(e) {
    var t = e.getDay();
    return 0 === t && (t = 7), t;
  }
  function w(e) {
    return Math.floor(e * Math.pow(10, 6)) / Math.pow(10, 6);
  }
  var T = 864e5;
  function j(e, t) {
    if (arguments.length < 1)
      throw new TypeError(
        "1 argument required, but only " + arguments.length + " present"
      );
    var r,
      a,
      o,
      i,
      s,
      c,
      f = 0,
      h = n(e),
      y = h.getTime();
    try {
      r = D(t);
    } catch (e) {
      r = D({});
    }
    return (
      (a =
        null != (s = r.timeZone)
          ? s
          : new Intl.DateTimeFormat().resolvedOptions().timeZone),
      (o = null == (c = r.locale) ? "en-US" : c),
      (i = null != (u = r.weekStartsOn) ? u : 0),
      r.timeZone ||
        console.warn(
          "Using the local timezone could lead to wrong results. Please pass the timeZone option explicitly. Read more about it here: https://git.io/JvXDl"
        ),
      null != (p = r.additionalDigits) &&
        0 !== p &&
        1 !== p &&
        2 !== p &&
        console.warn(
          "additionalDigits used to be a required argument, but now it's optional. Please avoid passing additional parameters at all, or explicitly pass '0'. Read more about it here: https://git.io/JvXD3"
        ),
      void 0 !== r.timestampIsSeconds &&
        (console.warn(
          "timestampIsSeconds is deprecated. Please use the `timestamp` option instead. Read more about it here: https://git.io/JvXDl"
        ),
        (f = r.timestampIsSeconds ? 1e3 : 1)),
      (function (e, t, n, r) {
        if (arguments.length < 1)
          throw new TypeError("1 argument required, but only none provided");
        if (null === e) return new Date(NaN);
        if ("object" == typeof e) return new Date(e.getTime());
        if ("function" == typeof e) return new Date(e());
        if ("string" == typeof e) {
          var a = String(e).match(
            /^(\d{4})-?(\d{1,2})-?(\d{0,2})[^0-9]*(\d{1,2})?:?(\d{1,2})?:?(\d{1,2})?.?(\d{1,7})?$/
          );
          if (a) {
            var o = new Date(
              +a[1],
              a[2] - 1 || 0,
              null == a[3] ? 1 : +a[3],
              +a[4] || 0,
              +a[5] || 0,
              +a[6] || 0,
              +((a[7] || "0") + "00").substring(0, 3)
            );
            return (
              n &&
                !r &&
                a[8] &&
                ((n = a[8].charAt(0)),
                ("-" !== n && "+" !== n) || (r = "-" === n),
                (n = a[8].substring(1, 3)),
                a[8].length > 3 && (r = void 0),
                o.setHours(
                  o.getHours() -
                    +n +
                    ((r ? -1 : 1) * +(a[8].substring(3, 5) || 0)) / 60
                )),
              o
            );
          }
        }
        var i = String(e),
          u = Date.parse(i);
        if (!isNaN(u)) return new Date(u);
        throw new Error("Invalid date string");
      })(e, 0, void 0, void 0),
      new Date(y)
    );
  }
  function D(e) {
    if (null === e || "object" != typeof e) return {};
    var t = {};
    for (var n in e) e.hasOwnProperty(n) && (t[n] = e[n]);
    return t;
  }
  (e.compareAsc = r),
    (e.compareDesc = function (e, t) {
      if (arguments.length < 2)
        throw new TypeError(
          "2 arguments required, but only " + arguments.length + " present"
        );
      var a = n(e),
        o = n(t),
        i = a.getTime() - o.getTime();
      return i > 0 ? -1 : i < 0 ? 1 : i;
    }),
    (e.default = {
      compareAsc: r,
      compareDesc: function (e, t) {
        if (arguments.length < 2)
          throw new TypeError(
            "2 arguments required, but only " + arguments.length + " present"
          );
        var a = n(e),
          o = n(t),
          i = a.getTime() - o.getTime();
        return i > 0 ? -1 : i < 0 ? 1 : i;
      },
      format: function (e, t) {
        return "formatted_date";
      },
      formatDistance: function (e, t) {
        return "formatted_distance";
      },
      getTime: c,
      getYear: function (e) {
        if (arguments.length < 1)
          throw new TypeError(
            "1 argument required, but only " + arguments.length + " present"
          );
        return n(e).getFullYear();
      },
      isAfter: o,
      isBefore: a,
      isEqual: s,
      isValid: u,
      parse: j,
      parseISO: function (e, t) {
        if (arguments.length < 1)
          throw new TypeError(
            "1 argument required, but only " + arguments.length + " present"
          );
        if (null === e) return new Date(NaN);
        var n = e.match(
          /^(\d{4})-?(\d{2})-?(\d{2})(?:[ T](\d{2}):?(\d{2}):?(\d{2})(?:\.(\d{1,}))?(Z|[\+\-]\d{2}:?\d{2})?)?$/
        );
        if (n) {
          var r = new Date(
            Date.UTC(
              +n[1],
              +n[2] - 1,
              +n[3],
              +(n[4] || 0),
              +(n[5] || 0),
              +(n[6] || 0),
              n[7] ? Math.floor(+("0." + n[7]) * 1e3) : 0
            )
          );
          if (n[8]) {
            if ("Z" !== n[8]) {
              var a = n[8].match(/^([\+\-])(\d{2}):?(\d{2})$/);
              if (a) {
                var o = +a[2] * 60 + (+a[3] || 0);
                r.setUTCMinutes(r.getUTCMinutes() - ("-" === a[1] ? -o : o));
              }
            }
            return r;
          }
          return r;
        }
        throw new Error("Invalid ISO date string");
      },
      startOfDay: d,
      toDate: n,
    }),
    Object.defineProperty(e, "__esModule", { value: !0 });
});
