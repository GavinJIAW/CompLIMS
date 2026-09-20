import { makeCrud } from '../shared/crud';
import { api } from './api';
export function createCrudOptions({ context }: any) { return makeCrud('service', api, context); }
