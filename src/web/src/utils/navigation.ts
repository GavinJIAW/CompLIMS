/** Isolate malformed records and their subtree; never invent a route identity. */
export function validRoutePath(route: any): boolean {
    if (route && typeof route.path === 'string' && route.path.trim().length > 0) return true;
    console.warn('Invalid navigation route: missing path', {
        id: route?.id, name: route?.title ?? route?.name, invalidField: 'path',
    });
    return false;
}
export function projectRouteTree(routes: any[]): any[] {
    if (!Array.isArray(routes)) throw new Error('Invalid navigation route collection');
    return routes.filter(validRoutePath).map(route => ({
        ...route,
        ...(route.children ? { children: projectRouteTree(route.children) } : {}),
    }));
}
