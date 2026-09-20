import {makeM2Crud} from '../../shared/m2Crud';
import {api} from './api';
export function createCrudOptions({context}:any){return makeM2Crud('contract',api,context);}
