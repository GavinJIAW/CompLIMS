<template>
  <div>
    {{ data }}
  </div>
</template>
<script setup lang="ts">
import {defineProps,ref,watch} from 'vue'
import {useDeptInfoStore} from '/@/stores/modules/dept'
const props = defineProps({
  modelValue:{
    type: Number || String
  }
})
const data = ref()
watch(()=>{
  return props.modelValue
},async (newVal)=>{
  const deptInfoStore = useDeptInfoStore()
  data.value = undefined;
  const result = await deptInfoStore.getParentDeptById(newVal).catch(() => {
    console.warn("Department display unavailable");
    return undefined;
  })
  if(result?.nodes){
    let name = ""
    result.nodes.forEach((item:any,index:number)=>{
      name +=  index>0?`/${item.name}`:item.name
    })
    data.value = name
  }
},{immediate: true} )
</script>
