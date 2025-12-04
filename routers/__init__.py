from routers.auth import router as auth_router
from routers.tenants import router as tenants_router
from routers.assets import router as assets_router
from routers.optimization import router as optimization_router
from routers.integrations import router as integrations_router
from routers.health import router as health_router
from routers.work_orders import router as work_orders_router

__all__ = [
    'auth_router', 'tenants_router', 'assets_router',
    'optimization_router', 'integrations_router', 'health_router',
    'work_orders_router'
]
