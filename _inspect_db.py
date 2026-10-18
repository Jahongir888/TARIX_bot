from database.models import User, UserSupervisor, SupervisorInvoice, Base
from web.server import app

print("User cols:", [c.name for c in User.__table__.columns])
print("has avatar", hasattr(User, "avatar_url"), User.avatar_url.type)
print("has secondary", hasattr(User, "secondary_phone"))
print("has is_subscribed", hasattr(User, "is_subscribed"), User.is_subscribed.default.arg)
print("has birth_date", hasattr(User, "birth_date"))
print("supervisor table", UserSupervisor.__tablename__)
print("invoice table", SupervisorInvoice.__tablename__)
routes = sorted({getattr(r, "path", None) for r in app.routes})
for p in ["/api/profile", "/api/supervisor/invite-link", "/api/user/profile/{telegram_id}"]:
    print(p, "OK" if p in routes else "MISSING")
print("import ok")
