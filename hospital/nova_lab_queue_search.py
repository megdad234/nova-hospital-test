"""NOVA laboratory work queue: read-only, server-side search/filter/pagination.

Independent of the legacy core.orders() 200-record limit. Only PAID/COMPLETED
orders are returned to laboratory staff, as before. Does not modify result
values, historic orders, approval, payment, invoices, pharmacy or printing.
Date filter uses the hospital server local date like core.now().
"""
from datetime import date, timedelta
import re


_PERIODS = {"today", "yesterday", "week", "all", "custom"}
_STATES = {"all", "waiting", "draft", "partial", "unfinished", "completed"}
_SORTS = {"newest": "DESC", "oldest": "ASC"}
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_ROLES = {"admin", "lab"}


def _day(value, label):
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise ValueError("تاريخ " + label + " غير صحيح")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("تاريخ " + label + " غير صحيح") from None
    if parsed.isoformat() != value:
        raise ValueError("تاريخ " + label + " غير صحيح")
    return parsed


def _number(value, default, label, maximum):
    if value is None or value == "":
        return default
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)):
        raise ValueError(label + " غير صحيح")
    number = int(value)
    if number < 1 or number > maximum:
        raise ValueError(label + " خارج الحدود")
    return number


def _escape_like(value):
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _selected_period(period, date_from, date_to, today):
    if period not in _PERIODS:
        raise ValueError("اختيار الفترة غير صحيح")
    if period == "all":
        return None, None
    if period == "today":
        return today, today
    if period == "yesterday":
        day = today - timedelta(days=1)
        return day, day
    if period == "week":
        return today - timedelta(days=6), today
    start = _day(date_from, "البداية")
    end = _day(date_to, "النهاية")
    if start > end:
        raise ValueError("تاريخ البداية بعد تاريخ النهاية")
    if (end - start).days > 3650:
        raise ValueError("الفترة المحددة طويلة جدًا")
    return start, end


def search_queue(conn, *, role, q="", period="today",
                 date_from="", date_to="", status="all", page=1,
                 page_size=25, sort="newest", current_day=None):
    """Return an independently filtered page of authorized lab orders.

    The older-unfinished count is independent of current date/search filters.
    All results use the original order IDs consumed by NOVA openDetails().
    """
    if role not in _ROLES:
        raise PermissionError("لا تملك صلاحية عرض طلبات المعمل")
    if not isinstance(q, str) or len(q) > 120:
        raise ValueError("البحث طويل جدًا")
    q = q.strip()
    if period not in _PERIODS or status not in _STATES or sort not in _SORTS:
        raise ValueError("فلتر طلبات المعمل غير صحيح")
    page = _number(page, 1, "رقم الصفحة", 100000)
    page_size = _number(page_size, 25, "حجم الصفحة", 50)
    now = current_day if current_day is not None else date.today()
    if not isinstance(now, date):
        raise TypeError("Hospital local date required")
    start, end = _selected_period(period, date_from, date_to, now)
    cond = ["o.status IN ('paid','completed')"]
    params = []
    if start is not None:
        cond.append("o.created_at >= ?")
        params.append(start.isoformat())
    if end is not None:
        cond.append("o.created_at < ?")
        params.append((end + timedelta(days=1)).isoformat())
    if q:
        term = "%" + _escape_like(q) + "%"
        cond.append("""(p.full_name LIKE ? ESCAPE '\\'
                    OR p.patient_no LIKE ? ESCAPE '\\'
                    OR o.order_no LIKE ? ESCAPE '\\'
                    OR EXISTS (
                        SELECT 1 FROM hospital_order_items ix
                        WHERE ix.order_id=o.id
                        AND ix.test_name LIKE ? ESCAPE '\\'
                    ))""")
        params.extend([term, term, term, term])
    base = """WITH listing AS (
        SELECT o.id, o.order_no, o.patient_id, o.status, o.created_at,
               o.total, p.full_name AS patient_name, p.patient_no,
               (SELECT count(*) FROM hospital_order_items i
                WHERE i.order_id=o.id) AS tests_count,
               (SELECT count(*) FROM hospital_order_items i
                WHERE i.order_id=o.id AND i.result_status='approved') AS approved_count,
               (SELECT count(*) FROM hospital_order_items i
                WHERE i.order_id=o.id AND i.result_status='draft') AS draft_count
        FROM hospital_orders o
        JOIN hospital_patients p ON p.id=o.patient_id
        WHERE """ + " AND ".join(cond) + ")"
    summary = conn.execute(base + """
        SELECT count(*) AS total,
            coalesce(sum(CASE WHEN tests_count>0 AND approved_count=0
                       AND draft_count=0 THEN 1 ELSE 0 END),0) AS waiting,
            coalesce(sum(CASE WHEN draft_count>0 THEN 1 ELSE 0 END),0) AS drafts,
            coalesce(sum(CASE WHEN approved_count>0
                       AND approved_count<tests_count THEN 1 ELSE 0 END),0) AS partial,
            coalesce(sum(CASE WHEN tests_count>0
                       AND approved_count=tests_count THEN 1 ELSE 0 END),0) AS completed,
            coalesce(sum(CASE WHEN approved_count<tests_count THEN 1 ELSE 0 END),0) AS unfinished
        FROM listing""", params).fetchone()
    labels = ["total", "waiting", "drafts", "partial", "completed", "unfinished"]
    counts = {key: int(summary[i] or 0) for i, key in enumerate(labels)}
    state_conditions = {
        "all": "1=1",
        "waiting": "tests_count>0 AND approved_count=0 AND draft_count=0",
        "draft": "draft_count>0",
        "partial": "approved_count>0 AND approved_count<tests_count",
        "unfinished": "approved_count<tests_count",
        "completed": "tests_count>0 AND approved_count=tests_count",
    }
    filtered = " WHERE " + state_conditions[status]
    total = conn.execute(base + " SELECT count(*) FROM listing" + filtered,
                         params).fetchone()[0]
    pages = max(1, (total + page_size - 1)//page_size)
    page = min(page, pages)
    offset = (page-1)*page_size
    direction = _SORTS[sort]
    cursor = conn.execute(base + """ SELECT id,order_no,patient_id,status,
        created_at,total,patient_name,patient_no,tests_count,approved_count,
        draft_count FROM listing """ + filtered +
        " ORDER BY created_at " + direction + ", id " + direction +
        " LIMIT ? OFFSET ?", params + [page_size, offset])
    cols = [d[0] for d in cursor.description]
    rows = [dict(zip(cols, tuple(row))) for row in cursor.fetchall()]
    old = conn.execute("""SELECT count(*) FROM hospital_orders o
        WHERE o.status IN ('paid','completed') AND o.created_at < ?
          AND EXISTS(SELECT 1 FROM hospital_order_items i
                     WHERE i.order_id=o.id AND i.result_status!='approved')""",
                       (now.isoformat(),)).fetchone()[0]
    return {"items": rows, "total": int(total), "page": page,
            "page_size": page_size, "pages": pages, "summary": counts,
            "older_unfinished": int(old), "period": period,
            "today": now.isoformat()}
