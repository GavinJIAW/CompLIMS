<template>
  <div>
    <el-card v-for="(group,index) in modelValue || []" :key="group.id || index" class="scheme">
      <template #header><div class="group-header">
        <el-input-number v-model="group.sequence" :min="0" :disabled="!can(group,'sequence',groupPermissions)" @change="publish" />
        <el-input v-model="group.name_snapshot" placeholder="商业分组名称" :disabled="!can(group,'name_snapshot',groupPermissions)" @change="publish" />
        <el-button type="danger" link :disabled="disabled" @click="removeGroup(index)">删除分组</el-button>
      </div></template>
      <template v-if="!group.id">
        <MasterSelect v-model="group.source_scheme" resource="scheme" :disabled="disabled || !groupPermissions.source_scheme?.is_create" @selected="schemeSelected(group,$event)" @update:model-value="publish" />
        <p v-if="group.source_scheme">保存时由服务器导入完整方案快照。保存后可编辑明细。</p>
        <p v-else>不选择来源方案时，此分组可直接添加产品。</p>
      </template>
      <el-input v-model="group.name_en_snapshot" placeholder="英文方案名称" :disabled="!can(group,'name_en_snapshot',groupPermissions)" @change="publish" />
      <el-input v-model="group.description_snapshot" type="textarea" placeholder="方案说明" :disabled="!can(group,'description_snapshot',groupPermissions)" @change="publish" />
      <el-input v-model="group.remark" placeholder="分组备注" :disabled="!can(group,'remark',groupPermissions)" @change="publish" />
      <template v-if="group.id || !group.source_scheme">
        <el-table :data="group.items || []" :row-key="rowKey" border>
          <el-table-column label="顺序" width="100"><template #default="{row}"><el-input-number v-model="row.sequence" :min="0" :controls="false" :disabled="!can(row,'sequence',itemPermissions)" @change="publish" /></template></el-table-column>
          <el-table-column label="产品 / 正式名称" min-width="240"><template #default="{row}">
            <MasterSelect v-if="!row.id" v-model="row.source_product" resource="product" :disabled="disabled || !itemPermissions.source_product?.is_create" @selected="productSelected(row,$event)" @update:model-value="publish" />
            <span v-else>{{row.product_number_snapshot}}</span>
            <el-input v-model="row.name_snapshot" :disabled="!can(row,'name_snapshot',itemPermissions)" @change="publish" />
          </template></el-table-column>
          <el-table-column label="英文名称" min-width="180"><template #default="{row}"><el-input v-model="row.name_en_snapshot" :disabled="!can(row,'name_en_snapshot',itemPermissions)" @change="publish" /></template></el-table-column>
          <el-table-column label="单位" width="100"><template #default="{row}"><el-input v-model="row.unit_snapshot" :disabled="!can(row,'unit_snapshot',itemPermissions)" @change="publish" /></template></el-table-column>
          <el-table-column label="商务数量" min-width="140"><template #default="{row}"><el-input v-model="row.quantity" :disabled="!can(row,'quantity',itemPermissions)" @change="publish" /></template></el-table-column>
          <el-table-column label="含税单价 / 元" min-width="150"><template #default="{row}"><el-input v-model="row.unit_price" :disabled="!can(row,'unit_price',itemPermissions)" @change="publish" /></template></el-table-column>
          <el-table-column label="行金额 / 元" min-width="140"><template #default="{row}">{{line(row) ?? row.line_amount ?? '—'}}</template></el-table-column>
          <el-table-column label="备注" min-width="140"><template #default="{row}"><el-input v-model="row.remark" :disabled="!can(row,'remark',itemPermissions)" @change="publish" /></template></el-table-column>
          <el-table-column type="expand"><template #default="{row}"><RequirementEditor :schema="row.requirement_schema || []" v-model="row.requirement_data" :disabled="!can(row,'requirement_data',itemPermissions)" @update:model-value="publish" /></template></el-table-column>
          <el-table-column label="操作" width="80"><template #default="{$index}"><el-button type="danger" link :disabled="disabled || !can(group,'items',groupPermissions)" @click="group.items.splice($index,1);publish()">删除</el-button></template></el-table-column>
        </el-table>
        <el-button :disabled="disabled || !can(group,'items',groupPermissions) || !itemPermissions.source_product?.is_create" @click="addItem(group)">添加产品</el-button>
      </template>
    </el-card>
    <el-button :disabled="disabled || !groupPermissions.sequence?.is_create" @click="addGroup">添加方案 / 自定义分组</el-button>
    <p>金额预览使用十进制定点运算；保存后以服务器返回的持久化金额为准。</p>
  </div>
</template>
<script setup lang="ts">
import MasterSelect from '../../shared/MasterSelect.vue';
import RequirementEditor from './RequirementEditor.vue';
import {multiply,sum} from '../../shared/decimal';
import {request} from '/@/utils/service';
const props=defineProps<{modelValue:any[];groupPermissions:any;itemPermissions:any;disabled?:boolean}>();
const emit=defineEmits(['update:modelValue']);
const can=(row:any,key:string,permissions:any)=>!props.disabled && !!permissions?.[key]?.[row.id?'is_update':'is_create'];
const publish=()=>emit('update:modelValue',[...(props.modelValue || [])]);
const line=(row:any)=>row.quantity!==undefined&&row.unit_price!==undefined?sum([multiply(row.quantity,row.unit_price)],2):null;
const next=(rows:any[])=>Math.max(0,...rows.map(row=>row.sequence || 0))+10;
const rowKey=(row:any)=>row.id || row._key || row.sequence;
const addGroup=()=>emit('update:modelValue',[...(props.modelValue || []),{sequence:next(props.modelValue || []),name_snapshot:'自定义分组',items:[]}]);
const removeGroup=(index:number)=>emit('update:modelValue',props.modelValue.filter((_,i)=>i!==index));
function addItem(group:any){group.items ||= [];group.items.push({_key:`new-${Date.now()}-${next(group.items)}`,sequence:next(group.items),quantity:'1.000000',requirement_data:{}});publish();}
function schemeSelected(group:any,scheme:any){if(group.id || !scheme)return;for(const [target,key] of Object.entries({name_snapshot:'name',name_en_snapshot:'name_en',description_snapshot:'description'}))if(can(group,target,props.groupPermissions)&&scheme[key]!==undefined)group[target]=scheme[key];publish();}
async function productSelected(row:any,product:any){
  if(row.id || !product || row._loaded===product.id)return;
  row._loaded=product.id;
  row.product_number_snapshot=product.number;
  for(const [target,key] of Object.entries({name_snapshot:'name',name_en_snapshot:'name_en',unit_snapshot:'unit',unit_price:'reference_price',requirement_data:'requirement_defaults'}))if(can(row,target,props.itemPermissions)&&product[key]!==undefined)row[target]=JSON.parse(JSON.stringify(product[key]));
  if(product.service){const {data}=await request({url:`/api/lims/service/${product.service}/`});row.requirement_schema=data.requirement_template || [];}
  publish();
}
</script>
<style scoped>.scheme{margin-bottom:16px}.group-header{display:flex;gap:12px;align-items:center}.scheme :deep(.el-input-number){max-width:90px}.scheme :deep(.el-input){margin-bottom:6px}</style>
