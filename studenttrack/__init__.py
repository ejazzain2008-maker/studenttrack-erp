import pymysql
pymysql.install_as_MySQLdb()

# Monkey-patch Django to bypass the MariaDB 10.6 version check
from django.db.backends.base.base import BaseDatabaseWrapper
BaseDatabaseWrapper.check_database_version_supported = lambda self: None
