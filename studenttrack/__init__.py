import pymysql
pymysql.install_as_MySQLdb()

# Monkey-patch Django to bypass the MariaDB 10.6 version check
from django.db.backends.base.base import BaseDatabaseWrapper
BaseDatabaseWrapper.check_database_version_supported = lambda self: None

# Monkey-patch Django's MySQL features to disable the RETURNING clause for MariaDB 10.4 compatibility
from django.db.backends.mysql.features import DatabaseFeatures
DatabaseFeatures.can_return_columns_from_insert = property(lambda self: False)
DatabaseFeatures.can_return_rows_from_bulk_insert = property(lambda self: False)
