"""Framework extensions initialized by the app factory."""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message_category = "warning"
csrf = CSRFProtect()
socketio = SocketIO(cors_allowed_origins="*")
limiter = Limiter(key_func=get_remote_address, default_limits=["300 per hour"])
