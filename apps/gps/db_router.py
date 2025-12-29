"""
Database Router for GPS Application
Routes read operations to analytics database and writes to default
"""


class GpsRouter:
    """
    A router to control database operations for GPS models
    - Write operations (INSERT/UPDATE/DELETE) use 'default' (gps_receiver user)
    - Read operations (SELECT) use 'analytics' (gps_analytics user) for better performance
    """
    
    def db_for_read(self, model, **hints):
        """
        Route read operations to analytics database
        """
        if model._meta.app_label == 'gps':
            return 'analytics'
        return None
    
    def db_for_write(self, model, **hints):
        """
        Route write operations to default database
        """
        if model._meta.app_label == 'gps':
            return 'default'
        return None
    
    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if both models are in gps app
        """
        if obj1._meta.app_label == 'gps' or obj2._meta.app_label == 'gps':
            return True
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Run migrations on default database only
        """
        if app_label == 'gps':
            return db == 'default'
        return None
