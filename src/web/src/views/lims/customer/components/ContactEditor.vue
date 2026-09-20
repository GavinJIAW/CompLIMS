<template>
  <div>
    <el-table :data="modelValue || []" border>
      <el-table-column v-for="(label,key) in labels" :key="key" :label="label" min-width="150">
        <template #default="{row}">
          <el-switch v-if="['enabled','is_default'].includes(key)" v-model="row[key]" :disabled="!can(row,key)" @change="publish" />
          <el-input v-else v-model="row[key]" :disabled="!can(row,key)" @change="publish" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80"><template #default="{$index}"><el-button type="danger" link :disabled="disabled" @click="remove($index)">删除</el-button></template></el-table-column>
    </el-table>
    <el-button :disabled="disabled || !permissions?.name?.is_create" @click="add">添加联系人</el-button>
    <p>最多一个启用的默认联系人。停用的默认联系人重新启用时仍须满足此约束。</p>
  </div>
</template>
<script setup lang="ts">
const props = defineProps<{modelValue?:any[]; permissions:any; disabled?:boolean}>();
const emit = defineEmits(['update:modelValue']);
const labels:Record<string,string> = {name:'姓名',department:'部门',title:'职务',phone:'电话',mobile:'手机',email:'邮箱',address:'联系地址',enabled:'启用',is_default:'默认',remark:'备注'};
const can = (row:any,key:string) => !props.disabled && !!props.permissions?.[key]?.[row.id ? 'is_update':'is_create'];
const publish = () => emit('update:modelValue',[...(props.modelValue || [])]);
const remove = (index:number) => emit('update:modelValue',(props.modelValue || []).filter((_,i)=>i!==index));
const add = () => emit('update:modelValue',[...(props.modelValue || []),{name:'',enabled:true,is_default:false}]);
</script>
